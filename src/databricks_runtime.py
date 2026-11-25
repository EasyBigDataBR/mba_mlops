"""Adaptador Databricks: entradas privadas, Delta, MLflow e orquestração.

Não modifica os objetos legados do schema. As tabelas ci_demo_* são exclusivas
deste exemplo. Somente marcadores de commit tornam snapshots/análises visíveis.
Execute um ciclo por vez; o Job fornecido tem concorrência máxima igual a 1.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

from src.data_pipeline import plan_snapshot

OWNER = "causalimpact_demo_v1"
DEFAULTS = {
    "catalog": "mba", "schema": "mlops_causalimpact",
    "source_mode": "drive",
    "source_path": "",
    "drive_connection": "", "as_of": "", "num_results": "300",
    "demo_id": "campanha_demo_v1", "max_files_per_run": "10",
    "experiment_path": "/Shared/MBA_CausalImpact_Demo",
}
SERIES_VALUES = [
    "observed", "counterfactual", "counterfactual_lower", "counterfactual_upper",
    "effect", "effect_lower", "effect_upper", "cumulative_effect",
    "cumulative_effect_lower", "cumulative_effect_upper",
]
TABLES = {
    "bronze": "demo_id STRING, filename STRING, sha256 STRING, content BINARY, byte_count BIGINT, received_at TIMESTAMP",
    "ingestion_control": "demo_id STRING, attempt_id STRING, recorded_at TIMESTAMP, filename STRING, sha256 STRING, status STRING, validation_status STRING, row_count BIGINT, errors_json STRING, superseded_by STRING",
    "silver": "demo_id STRING, snapshot_id STRING, date DATE, treated BIGINT, control_a BIGINT, control_b BIGINT, source_file STRING, source_sha256 STRING, source_revision BIGINT",
    "snapshots": "demo_id STRING, snapshot_id STRING, committed_at TIMESTAMP, as_of DATE, row_count BIGINT, files_json STRING, manifest_sha256 STRING, source_mode STRING",
    "analysis": "demo_id STRING, analysis_id STRING, snapshot_id STRING, committed_at TIMESTAMP, as_of DATE, row_count BIGINT, post_days BIGINT, average_effect DOUBLE, average_effect_lower DOUBLE, average_effect_upper DOUBLE, cumulative_effect DOUBLE, cumulative_effect_lower DOUBLE, cumulative_effect_upper DOUBLE, relative_effect DOUBLE, posterior_tail_probability DOUBLE, mlflow_run_id STRING, code_sha256 STRING, result_json STRING",
    "effects": "demo_id STRING, analysis_id STRING, date DATE, period STRING, " + ", ".join(f"{x} DOUBLE" for x in SERIES_VALUES),
    "executions": "demo_id STRING, event_id STRING, attempt_id STRING, recorded_at TIMESTAMP, stage STRING, status STRING, message STRING, snapshot_id STRING, analysis_id STRING",
}


class DataGateError(RuntimeError):
    """O ciclo não pode publicar uma nova análise."""


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, allow_nan=False, default=str)


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def ident(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError("Catálogo e schema devem conter letras, números e underscore.")
    return f"`{value}`"


def read_widgets(dbutils):
    """Job parameters prevalecem: criar widgets não sobrescreve valores existentes."""
    for key, default in DEFAULTS.items():
        try:
            dbutils.widgets.get(key)
        except Exception:
            dbutils.widgets.text(key, default)
    return validate_config({key: dbutils.widgets.get(key) for key in DEFAULTS})


def validate_config(raw):
    cfg = {**DEFAULTS, **raw}
    ident(cfg["catalog"])
    ident(cfg["schema"])
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", cfg["demo_id"]):
        raise ValueError("demo_id: use até 64 letras, números, underscore ou hífen.")
    cfg["num_results"] = int(cfg["num_results"])
    cfg["max_files_per_run"] = int(cfg["max_files_per_run"])
    if not 100 <= cfg["num_results"] <= 5000:
        raise ValueError("num_results deve estar entre 100 e 5000.")
    if not 1 <= cfg["max_files_per_run"] <= 10:
        raise ValueError("Este demonstrador aceita de 1 a 10 arquivos por leitura.")
    if cfg["as_of"]:
        if date.fromisoformat(cfg["as_of"]).isoformat() != cfg["as_of"]:
            raise ValueError("as_of deve usar AAAA-MM-DD.")
    if cfg["source_mode"] == "volume":
        if not re.fullmatch(r"/Volumes/[A-Za-z0-9_]+/[A-Za-z0-9_]+/[A-Za-z0-9_]+(?:/[A-Za-z0-9_-]+)+/?", cfg["source_path"]):
            raise ValueError("Use uma subpasta dedicada /Volumes/catalog/schema/volume/pasta.")
    elif cfg["source_mode"] == "drive":
        url = urlparse(cfg["source_path"])
        if url.scheme != "https" or url.hostname != "drive.google.com" or "/folders/" not in url.path:
            raise ValueError("No modo drive, informe em source_path a URL HTTPS da subpasta Entrada autorizada, não da raiz que contém Reserva.")
        if not cfg["drive_connection"]:
            raise ValueError("Informe a conexão Unity Catalog em drive_connection.")
    else:
        raise ValueError("source_mode deve ser volume ou drive; não há fallback automático.")
    if not cfg["experiment_path"].startswith("/"):
        raise ValueError("Informe um caminho absoluto de experimento MLflow do workspace.")
    return cfg


def code_fingerprint(root):
    paths = sorted((Path(root) / "src").glob("*.py")) + [Path(root) / "requirements.txt"]
    h = hashlib.sha256()
    for path in paths:
        h.update(path.relative_to(root).as_posix().encode())
        h.update(b"\0")
        h.update(path.read_bytes())
    return h.hexdigest()


def snapshot_hash(data):
    frame = data[["date", "treated", "control_a", "control_b"]].copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    for col in ["treated", "control_a", "control_b"]:
        frame[col] = frame[col].astype("int64")
    content = frame.sort_values("date").to_csv(index=False, lineterminator="\n").encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def verify_effect_rows(saved, expected):
    """Uma retomada só publica se todas as saídas persistidas conferirem."""
    actual = saved.to_dict("records") if isinstance(saved, pd.DataFrame) else saved
    normalize_date = lambda value: pd.Timestamp(value).date().isoformat()
    left = {normalize_date(r["date"]): r for r in actual}
    right = {normalize_date(r["date"]): r for r in expected}
    if len(left) != len(actual) or len(right) != len(expected) or set(left) != set(right):
        raise RuntimeError("Datas/contagem dos efeitos persistidos divergem do resultado.")
    for day, wanted in right.items():
        got = left[day]
        if got["period"] != wanted["period"]:
            raise RuntimeError(f"Período divergente em {day}.")
        for column in SERIES_VALUES:
            a, b = got[column], wanted[column]
            if pd.isna(a) and pd.isna(b):
                continue
            if pd.isna(a) or pd.isna(b) or not math.isclose(float(a), float(b), rel_tol=1e-9, abs_tol=1e-9):
                raise RuntimeError(f"Saída persistida divergente em {day}/{column}; nenhum marcador publicado.")


def panel_state(latest_ingest, latest_model_attempt, selected_analysis):
    if not selected_analysis:
        return "NO_ANALYSIS"
    if (not latest_ingest or latest_ingest["status"] not in {"READY", "REUSED"}
        or not latest_model_attempt or latest_model_attempt["status"] not in {"SUCCESS", "NO_CHANGE"}
        or latest_model_attempt["attempt_id"] != latest_ingest["attempt_id"]
        or latest_model_attempt["analysis_id"] != selected_analysis["analysis_id"]
        or latest_ingest["snapshot_id"] != selected_analysis["snapshot_id"]):
        return "PREVIOUS_VALID_RESULT"
    return "CONSISTENT"


def source_metadata_index(rows, max_files):
    """Valida os metadados antes de trazer os bytes para Python.

    filename vem de _metadata.file_name. source_path é a origem completa e
    pode ser uma URL Drive terminada em /view; nunca se deriva o nome da URL.
    """
    if len(rows) > max_files:
        raise DataGateError("Há mais CSVs do que o limite do demonstrador. Use uma pasta dedicada com até 10 arquivos.")
    indexed, paths, total = {}, set(), 0
    for row in rows:
        try:
            filename, source_path, length = row["filename"], row["source_path"], row["length"]
        except (KeyError, TypeError) as error:
            raise DataGateError("Metadados incompletos: selecione _metadata.file_name, path e length.") from error
        if (not isinstance(filename, str) or not filename or not filename.endswith(".csv")
            or any(char in filename for char in ("/", "\\", "\x00", "\n", "\r"))):
            raise DataGateError("_metadata.file_name deve conter o nome completo de um CSV, sem diretórios.")
        if not isinstance(source_path, str) or not source_path:
            raise DataGateError("A origem completa do arquivo não foi informada nos metadados.")
        if filename in indexed:
            raise DataGateError(f"Nome de CSV repetido na origem ou em subpastas: {filename}. Mantenha nomes únicos.")
        if source_path in paths:
            raise DataGateError("A mesma origem foi listada mais de uma vez; interrompa e revise os metadados.")
        if isinstance(length, bool) or not isinstance(length, int) or length < 0 or length > 1_000_000:
            raise DataGateError("Fonte excede 1 MB por arquivo ou informou um tamanho inválido.")
        indexed[filename] = {"source_path": source_path, "length": length}
        paths.add(source_path)
        total += length
    if total > 5_000_000:
        raise DataGateError("Fonte excede o limite didático de 5 MB no total.")
    return indexed


def source_files_from_rows(rows, metadata):
    """Associa nome e bytes sem confundir uma URL com o nome do arquivo."""
    files, origins = {}, {}
    for row in rows:
        filename = row["filename"]
        if filename not in metadata or filename in files:
            raise DataGateError("A lista de arquivos mudou durante a leitura ou contém nomes duplicados; tente novamente.")
        expected = metadata[filename]
        if row["source_path"] != expected["source_path"] or row["length"] != expected["length"]:
            raise DataGateError("Nome, origem ou tamanho mudou entre a descoberta e a leitura; tente novamente.")
        content = row["content"]
        if not isinstance(content, (bytes, bytearray, memoryview)):
            raise DataGateError(f"Conteúdo binário ausente ou inválido para {filename}.")
        payload = bytes(content)
        if len(payload) != expected["length"]:
            raise DataGateError(f"Quantidade de bytes diverge dos metadados de {filename}; tente novamente.")
        files[filename] = payload
        origins[filename] = row["source_path"]
    if set(files) != set(metadata):
        raise DataGateError("Um arquivo desapareceu entre a descoberta e a leitura; tente novamente.")
    return files, origins


def describe_source_files(files, origins, received_rows, accepted_files=None):
    """NEW/UNCHANGED usa o par nome+SHA já recebido na bronze, sem aprovar dados.

    Os arquivos do último snapshot aceito continuam imutáveis. A releitura de
    todos os arquivos limitados é intencional; não é transferência incremental.
    """
    if set(files) != set(origins):
        raise DataGateError("Faltam metadados de origem para os arquivos recebidos.")
    hashes = {name: hashlib.sha256(payload).hexdigest() for name, payload in files.items()}
    accepted_files = accepted_files or {}
    missing = sorted(set(accepted_files) - set(files))
    changed = sorted(name for name in accepted_files if name in hashes and accepted_files[name] != hashes[name])
    if missing or changed:
        raise DataGateError(f"Não remova nem sobrescreva entregas já aceitas. Ausentes={missing}; alteradas={changed}. Correções chegam em arquivo novo.")
    received = {(row["filename"], row["sha256"]) for row in received_rows}
    details = [{"filename": name, "source_path": origins[name], "sha256": hashes[name],
                "byte_count": len(files[name]),
                "status": "UNCHANGED" if (name, hashes[name]) in received else "NEW"}
               for name in sorted(files)]
    new_count = sum(item["status"] == "NEW" for item in details)
    return {"comparison_basis": "BRONZE_FILENAME_SHA256", "read_mode": "BOUNDED_FULL_READ",
            "file_count": len(files), "total_bytes": sum(len(payload) for payload in files.values()),
            "new_file_count": new_count, "unchanged_file_count": len(files) - new_count,
            "validation_is_separate": True, "files": details}


class DemoRuntime:
    def __init__(self, spark, dbutils, config, root):
        self.spark, self.dbutils = spark, dbutils
        self.cfg = validate_config(config)
        self.root = Path(root)
        self.namespace = f"{ident(self.cfg['catalog'])}.{ident(self.cfg['schema'])}"
        self.manifest_bytes = (self.root / "data_demo" / "manifest.json").read_bytes()
        self.manifest = json.loads(self.manifest_bytes)
        self.manifest_sha = hashlib.sha256(self.manifest_bytes).hexdigest()
        self.code_sha = code_fingerprint(self.root)
        self.spark.conf.set("spark.sql.session.timeZone", "UTC")

    def table(self, short):
        if short not in TABLES:
            raise ValueError("Tabela não pertence ao case.")
        return f"{self.namespace}.`ci_demo_{short}`"

    def setup(self, create_input_dir=False):
        # O catálogo mba deve existir e ser acessível à identidade da execução.
        self.spark.sql(f"CREATE SCHEMA IF NOT EXISTS {self.namespace}")
        for short, ddl in TABLES.items():
            name = self.table(short)
            if self.spark.catalog.tableExists(name):
                props = {r['key']: r['value'] for r in self.spark.sql(f"SHOW TBLPROPERTIES {name}").collect()}
                if props.get("mba_mlops_demo") != OWNER:
                    raise RuntimeError(f"{name} já existe e não foi criado por este demonstrador. Nada foi substituído.")
            else:
                self.spark.sql(f"CREATE TABLE {name} ({ddl}) USING DELTA TBLPROPERTIES ('mba_mlops_demo'='{OWNER}')")
            expected = [(part.strip().split()[0], part.strip().split()[1].lower()) for part in ddl.split(',')]
            actual = [(f.name, f.dataType.simpleString()) for f in self.spark.table(name).schema.fields]
            if expected != actual:
                raise RuntimeError(f"Schema incompatível em {name}; pare e revise a migração explicitamente.")
        if create_input_dir and self.cfg["source_mode"] == "volume":
            parts = self.cfg["source_path"].strip("/").split("/")
            vol = ".".join(ident(x) for x in parts[1:4])
            self.spark.sql(f"CREATE VOLUME IF NOT EXISTS {vol}")
            self.dbutils.fs.mkdirs(self.cfg["source_path"])
        return {"namespace": self.namespace, "tables": ["ci_demo_" + x for x in TABLES],
                "source_mode": self.cfg["source_mode"], "synthetic": True}

    def frame(self, short):
        from pyspark.sql import functions as F
        return self.spark.table(self.table(short)).where(F.col("demo_id") == self.cfg["demo_id"])

    def latest(self, short, **filters):
        from pyspark.sql import functions as F
        frame = self.frame(short)
        for key, value in filters.items():
            frame = frame.where(F.col(key) == value)
        order = "committed_at" if short in {"analysis", "snapshots"} else "recorded_at"
        rows = frame.orderBy(F.col(order).desc()).limit(1).collect()
        return rows[0].asDict(recursive=True) if rows else None

    def insert_once(self, short, rows, keys):
        """MERGE insert-only: uma retomada não duplica fatos nem reescreve histórico."""
        if not rows:
            return
        from pyspark.sql import functions as F
        name = self.table(short)
        schema = self.spark.table(name).schema
        complete = [{"demo_id": self.cfg["demo_id"], **r} for r in rows]
        data = self.spark.createDataFrame(complete, schema=schema)
        if data.groupBy(*keys).count().where(F.col("count") > 1).limit(1).count():
            raise RuntimeError(f"Chaves repetidas antes de persistir {short}.")
        temp = "ci_in_" + uuid.uuid4().hex
        data.createOrReplaceTempView(temp)
        on = " AND ".join(f"t.`{k}` = s.`{k}`" for k in keys)
        try:
            self.spark.sql(f"MERGE INTO {name} t USING `{temp}` s ON {on} WHEN NOT MATCHED THEN INSERT *")
        finally:
            self.spark.catalog.dropTempView(temp)

    def event(self, attempt, stage, status, message, snapshot_id=None, analysis_id=None):
        row = {"event_id": uuid.uuid4().hex, "attempt_id": attempt, "recorded_at": now(),
               "stage": stage, "status": status, "message": message,
               "snapshot_id": snapshot_id, "analysis_id": analysis_id}
        self.insert_once("executions", [row], ["demo_id", "event_id"])

    def read_source_bytes(self):
        """Retorna (files, origins) lendo só a fonte; não consulta/escreve Delta."""
        from pyspark.sql import functions as F
        reader = self.spark.read.format("binaryFile").option("pathGlobFilter", "*.csv")
        if self.cfg["source_mode"] == "drive":
            # No Drive a leitura é recursiva, inclusive se false for informado.
            reader = (reader.option("databricks.connection", self.cfg["drive_connection"])
                      .option("recursiveFileLookup", True))
        # Metadados primeiro: não trazer conteúdo ilimitado para a sessão Python.
        # _metadata é oculto: selecionar o nome explicitamente na leitura.
        # path permanece separado como origem; no Drive ele é uma URL completa.
        raw = reader.load(self.cfg["source_path"]).select(
            F.col("_metadata.file_name").alias("filename"),
            F.col("path").alias("source_path"), "length", "content")
        metadata_rows = raw.select("filename", "source_path", "length").limit(self.cfg["max_files_per_run"] + 1).collect()
        metadata = source_metadata_index(metadata_rows, self.cfg["max_files_per_run"])
        paths = [item["source_path"] for item in metadata.values()]
        rows = (raw.where(F.col("source_path").isin(paths))
                .select("filename", "source_path", "length", "content").collect()) if paths else []
        return source_files_from_rows(rows, metadata)

    def read_source(self):
        """Preserva a interface {filename: bytes}; exige setup das tabelas demo."""
        from pyspark.sql import functions as F
        self._source_discovery = None
        files, origins = self.read_source_bytes()
        previous = self.latest("snapshots")
        old_files = json.loads(previous["files_json"]) if previous else {}
        received = (self.frame("bronze").where(F.col("filename").isin(list(files)))
                    .select("filename", "sha256").distinct().collect()) if files else []
        self._source_discovery = describe_source_files(files, origins, received, old_files)
        return files

    def ingest(self, attempt=None):
        attempt = attempt or uuid.uuid4().hex
        try:
            files = self.read_source()
            discovery = self._source_discovery
            received = now()
            self.insert_once("bronze", [{"filename": n, "sha256": hashlib.sha256(b).hexdigest(),
                "content": b, "byte_count": len(b), "received_at": received} for n, b in files.items()],
                ["demo_id", "filename", "sha256"])
            plan = plan_snapshot(files, self.manifest)
            events = [{"attempt_id": attempt, "recorded_at": now(), "filename": e["filename"],
                       "sha256": e["sha256"], "status": e["status"],
                       "validation_status": e.get("validation_status", e["status"]),
                       "row_count": int(e.get("row_count", 0)), "errors_json": dumps(e.get("errors", [])),
                       "superseded_by": e.get("superseded_by")} for e in plan["events"]]
            self.insert_once("ingestion_control", events, ["demo_id", "attempt_id", "filename", "sha256"])
            if plan["status"] != "READY":
                self.event(attempt, "INGEST", plan["status"], dumps({**plan["summary"], "discovery": discovery}))
                raise DataGateError(f"Entrada {plan['status']}. Consulte ci_demo_ingestion_control. Nenhum novo snapshot/análise foi publicado.")
            data = plan["data"].copy()
            if self.cfg["as_of"]:
                cutoff = self.cfg["as_of"]
                if cutoff > plan["as_of"]:
                    raise DataGateError("as_of solicitado excede o último dia completo disponível.")
                data = data[pd.to_datetime(data["date"]) <= pd.Timestamp(cutoff)].copy()
                minimum = self.manifest["pre_days"] + self.manifest["initial_post_days"]
                if len(data) < minimum:
                    raise DataGateError("Corte solicitado não tem os 84 dias pré e 14 dias pós iniciais.")
            snapshot = snapshot_hash(data)
            as_of = pd.to_datetime(data["date"]).max().date()
            existing = self.latest("snapshots", snapshot_id=snapshot)
            if not existing:
                records = []
                for row in data.to_dict("records"):
                    records.append({"snapshot_id": snapshot, "date": pd.Timestamp(row["date"]).date(),
                                    **{c: int(row[c]) for c in ["treated", "control_a", "control_b", "source_revision"]},
                                    "source_file": row["source_file"], "source_sha256": row["source_sha256"]})
                self.insert_once("silver", records, ["demo_id", "snapshot_id", "date"])
                from pyspark.sql import functions as F
                saved = self.frame("silver").where(F.col("snapshot_id") == snapshot).toPandas()
                if len(saved) != len(data) or snapshot_hash(saved) != snapshot:
                    raise RuntimeError("Verificação do snapshot persistido falhou; marcador não foi gravado.")
                self.insert_once("snapshots", [{"snapshot_id": snapshot, "committed_at": now(), "as_of": as_of,
                    "row_count": len(data), "files_json": dumps({n: hashlib.sha256(b).hexdigest() for n, b in files.items()}),
                    "manifest_sha256": self.manifest_sha, "source_mode": self.cfg["source_mode"]}], ["demo_id", "snapshot_id"])
            status = "REUSED" if existing else "READY"
            self.event(attempt, "INGEST", status,
                       dumps({"row_count": len(data), "as_of": as_of.isoformat(), "discovery": discovery}),
                       snapshot_id=snapshot)
            return {"attempt_id": attempt, "status": status, "snapshot_id": snapshot,
                    "as_of": as_of.isoformat(), "row_count": len(data), "events": plan["events"],
                    "discovery": discovery}
        except DataGateError as error:
            last = self.latest("executions", stage="INGEST")
            if not last or last["attempt_id"] != attempt:
                self.event(attempt, "INGEST", "BLOCKED", str(error))
            raise
        except Exception as error:
            self.event(attempt, "INGEST", "ERROR", type(error).__name__ + ": " + str(error)[:1200])
            raise

    def analyze(self, ingestion=None):
        from pyspark.sql import functions as F
        from src.causal_model import run_causal_analysis, dependency_versions
        last = ingestion or self.latest("executions", stage="INGEST")
        if not last or last["status"] not in {"READY", "REUSED"}:
            raise DataGateError("Execute 01 com entrada válida antes de 02. A tentativa de ingestão mais recente não está liberada.")
        attempt, snapshot = last["attempt_id"], last["snapshot_id"]
        marker = self.latest("snapshots", snapshot_id=snapshot)
        if marker is None:
            raise DataGateError("Snapshot sem marcador de commit; execute a ingestão novamente.")
        model_cfg = {"pre_start": self.manifest["pre_start"], "intervention_date": self.manifest["intervention_date"],
                     "as_of": marker["as_of"].isoformat(), "num_results": self.cfg["num_results"], "run_placebo": False}
        fingerprint = {"snapshot_id": snapshot, "model_config": model_cfg, "code_sha256": self.code_sha,
                       "dependencies": dependency_versions()}
        analysis_id = hashlib.sha256(dumps(fingerprint).encode()).hexdigest()
        existing = self.latest("analysis", analysis_id=analysis_id)
        if existing:
            self.event(attempt, "ANALYSIS", "NO_CHANGE", "Mesmos dados, código, configuração e dependências; resultado reutilizado.", snapshot, analysis_id)
            return json.loads(existing["result_json"])
        try:
            data = self.frame("silver").where(F.col("snapshot_id") == snapshot).orderBy("date").toPandas()
            if len(data) != marker["row_count"] or snapshot_hash(data) != snapshot:
                raise RuntimeError("Snapshot persistido não corresponde ao marcador.")
            import mlflow
            mlflow.set_experiment(self.cfg["experiment_path"])
            with mlflow.start_run(run_name="causalimpact_" + model_cfg["as_of"]) as run:
                mlflow.set_tags({"demo_id": self.cfg["demo_id"], "data_kind": "synthetic", "engine": "google/tfp-causalimpact",
                                 "snapshot_id": snapshot, "analysis_id": analysis_id, "code_sha256": self.code_sha})
                mlflow.log_params(model_cfg)
                result = run_causal_analysis(data, model_cfg)
                result["runtime"] = {"analysis_id": analysis_id, "snapshot_id": snapshot, "code_sha256": self.code_sha,
                                     "mlflow_run_id": run.info.run_id, "execution_environment": "DATABRICKS", "synthetic": True}
                mlflow.log_metrics({k: float(v) for k, v in result["summary"].items()
                                    if isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)})
                mlflow.log_dict(result, "causalimpact/result.json")
                mlflow.log_dict(fingerprint, "causalimpact/fingerprint.json")
                mlflow.log_dict(json.loads(marker["files_json"]), "causalimpact/input_files_sha256.json")
                mlflow.log_text(data[["date", "treated", "control_a", "control_b"]].to_csv(index=False), "causalimpact/accepted_snapshot.csv")
                mlflow_run_id = run.info.run_id
            effect_rows = [{"analysis_id": analysis_id, "date": date.fromisoformat(row["date"]),
                            "period": row["period"], **{c: row[c] for c in SERIES_VALUES}} for row in result["series"]]
            self.insert_once("effects", effect_rows, ["demo_id", "analysis_id", "date"])
            persisted_effects = self.frame("effects").where(F.col("analysis_id") == analysis_id).orderBy("date").toPandas()
            verify_effect_rows(persisted_effects, result["series"])
            summary = result["summary"]
            numeric = ["average_effect", "average_effect_lower", "average_effect_upper", "cumulative_effect",
                       "cumulative_effect_lower", "cumulative_effect_upper", "relative_effect", "posterior_tail_probability"]
            self.insert_once("analysis", [{"analysis_id": analysis_id, "snapshot_id": snapshot,
                "committed_at": now(), "as_of": marker["as_of"], "row_count": len(data), "post_days": result["counts"]["post_days"],
                **{c: float(summary[c]) for c in numeric}, "mlflow_run_id": mlflow_run_id,
                "code_sha256": self.code_sha, "result_json": dumps(result)}], ["demo_id", "analysis_id"])
            self.event(attempt, "ANALYSIS", "SUCCESS", "Estimativa e evidências persistidas. Validade causal não é aprovação automática.", snapshot, analysis_id)
            return result
        except Exception as error:
            self.event(attempt, "ANALYSIS", "ERROR", type(error).__name__ + ": " + str(error)[:1200], snapshot, analysis_id)
            raise

    def panel(self):
        """Read-only. O último resultado válido e a última tentativa são separados."""
        from pyspark.sql import functions as F
        latest_attempt = self.latest("executions")
        latest_ingest = self.latest("executions", stage="INGEST")
        latest_model_attempt = self.latest("executions", stage="ANALYSIS")
        completed = (self.frame("executions").where((F.col("stage") == "ANALYSIS") &
                     F.col("status").isin("SUCCESS", "NO_CHANGE"))
                     .orderBy(F.col("recorded_at").desc()).limit(1).collect())
        latest_analysis = (self.latest("analysis", analysis_id=completed[0]["analysis_id"])
                           if completed else self.latest("analysis"))
        if not latest_analysis:
            return {"status": "NO_ANALYSIS", "latest_attempt": latest_attempt, "latest_ingest": latest_ingest,
                    "history": self.frame("executions").orderBy(F.col("recorded_at").desc()), "effects": None,
                    "summary": None, "checks": []}
        result = json.loads(latest_analysis["result_json"])
        effects = self.frame("effects").where(F.col("analysis_id") == latest_analysis["analysis_id"]).orderBy("date")
        data = effects.toPandas()
        post = data[data["period"] == "POST"]
        checks = [
            {"check": "Linhas do resultado", "passed": len(data) == latest_analysis["row_count"]},
            {"check": "Uma linha por dia", "passed": not data["date"].duplicated().any()},
            {"check": "Pós sem valores ausentes", "passed": not post[SERIES_VALUES].isna().any().any()},
            {"check": "Intervalo pontual ordenado", "passed": bool((post["effect_lower"] <= post["effect_upper"]).all())},
            {"check": "Acumulado final confere", "passed": bool(len(post) and math.isclose(float(post.iloc[-1]["cumulative_effect"]), latest_analysis["cumulative_effect"], rel_tol=1e-8))},
            {"check": "Run MLflow registrada", "passed": bool(latest_analysis["mlflow_run_id"])},
        ]
        state = panel_state(latest_ingest, latest_model_attempt, latest_analysis)
        if not all(c["passed"] for c in checks):
            state = "INCONSISTENT"
        return {"status": state, "latest_attempt": latest_attempt, "latest_ingest": latest_ingest,
                "latest_analysis": {k: v for k, v in latest_analysis.items() if k != "result_json"},
                "summary": result["summary"], "effects": effects, "checks": checks,
                "history": self.frame("analysis").drop("result_json").orderBy("committed_at")}

    def run_cycle(self):
        self.setup()
        ingestion = self.ingest()
        result = self.analyze(ingestion)
        panel = self.panel()
        if panel["status"] != "CONSISTENT":
            self.event(ingestion["attempt_id"], "VALIDATION", "ERROR", dumps(panel["checks"]), ingestion["snapshot_id"], result["runtime"]["analysis_id"])
            raise RuntimeError("A conferência final não está consistente. Revise as tabelas de auditoria.")
        self.event(ingestion["attempt_id"], "VALIDATION", "SUCCESS", "Conferência de integridade aprovada.", ingestion["snapshot_id"], result["runtime"]["analysis_id"])
        return {"ingestion": ingestion, "result": result, "panel": panel}


def plot_effects(effects, intervention_date):
    """Três gráficos: observado/contrafactual, efeito diário e acumulado."""
    import matplotlib.pyplot as plt
    data = effects.toPandas() if hasattr(effects, "toPandas") else effects.copy()
    data["date"] = pd.to_datetime(data["date"])
    post = data[data["period"] == "POST"]
    fig, axes = plt.subplots(3, 1, figsize=(12, 9), sharex=True, constrained_layout=True)
    axes[0].plot(data["date"], data["observed"], label="Observado", color="#003f5c")
    axes[0].plot(data["date"], data["counterfactual"], label="Sem campanha (estimado)", color="#ef8a17")
    axes[0].fill_between(data["date"], data["counterfactual_lower"], data["counterfactual_upper"], color="#ef8a17", alpha=.18, label="Intervalo de 95%")
    for ax, metric, title in [(axes[1], "effect", "Efeito diário estimado"), (axes[2], "cumulative_effect", "Efeito acumulado estimado")]:
        ax.plot(post["date"], post[metric], color="#007f86")
        ax.fill_between(post["date"], post[metric + "_lower"], post[metric + "_upper"], color="#007f86", alpha=.18)
        ax.axhline(0, color="#777777", linewidth=.8)
        ax.set_title(title, loc="left")
    for ax in axes:
        ax.axvline(pd.Timestamp(intervention_date), linestyle="--", color="#666666", linewidth=.8)
        ax.set_ylabel("Conversões sintéticas")
        ax.grid(alpha=.15)
    axes[0].set_title("Campanha demonstrativa · dados sintéticos", loc="left")
    axes[0].legend(loc="upper left", ncol=3)
    return fig
