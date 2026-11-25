# Databricks notebook source

# MAGIC %md
# MAGIC # Inventário do projeto — somente leitura
# MAGIC
# MAGIC **Destino:** `mba.mlops_causalimpact`.
# MAGIC
# MAGIC Execute este notebook no próprio Databricks e copie o JSON da última célula
# MAGIC para um arquivo `inventario_mlops_causalimpact.json`, que poderá ser anexado.
# MAGIC
# MAGIC O inventário consulta nomes e esquemas, versões de pacotes e metadados do
# MAGIC modelo confirmado. Não lê registros de negócio, não lista arquivos do
# MAGIC volume, não executa funções/modelos e não altera objetos.
# MAGIC
# MAGIC Objetos ausentes podem estar invisíveis por permissão. Uma consulta que
# MAGIC falha não comprova que o objeto não existe. Este inventário não substitui
# MAGIC a exportação dos notebooks reais em **Source ZIP**.
# MAGIC
# MAGIC **Estado da preparação:** código revisado, ainda não executado no workspace.

# COMMAND ----------

import json
import platform
import re
from datetime import datetime, timezone
from importlib import metadata

CATALOG = "mba"
SCHEMA = "mlops_causalimpact"
MODEL_NAME = f"{CATALOG}.{SCHEMA}.bh_counterfactual_model"

MAX_OBJECTS = 300
MAX_COLUMNS = 2000
MAX_MODEL_VERSIONS = 50


def quote_identifier(value):
    if not isinstance(value, str) or not value or any(ord(c) < 32 for c in value):
        raise ValueError("Identificador inválido.")
    return "`" + value.replace("`", "``") + "`"


def sql_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


def safe_error(error):
    """Não devolve mensagem bruta, stack trace, URLs ou configuração de autenticação."""
    code = None
    for method_name in ("getCondition", "getErrorClass"):
        try:
            method = getattr(error, method_name, None)
            candidate = method() if callable(method) else None
            if candidate and re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", str(candidate)):
                code = str(candidate)
                break
        except Exception:
            pass
    if code is None:
        candidate = getattr(error, "error_code", None)
        if candidate and re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", str(candidate)):
            code = str(candidate)
    return {
        "status": "INDISPONIVEL_OU_ERRO",
        "exception_type": type(error).__name__,
        "error_code": code,
        "orientacao": (
            "Verifique disponibilidade e permissões no Databricks. "
            "Detalhes brutos do erro foram omitidos."
        ),
    }


spark_session = globals().get("spark")
namespace_sql = ".".join(quote_identifier(v) for v in (CATALOG, SCHEMA))
information_schema_sql = (
    quote_identifier(CATALOG) + "." + quote_identifier("information_schema")
)


def read_metadata(sql, limit):
    """Usada abaixo apenas com SHOW TABLES ou SELECT em information_schema."""
    if spark_session is None:
        return {"status": "NAO_EXECUTADO", "motivo": "Sessão Spark não disponível."}
    try:
        rows = spark_session.sql(sql).limit(limit + 1).collect()
        return {
            "status": "OK",
            "truncated": len(rows) > limit,
            "returned_metadata_items": min(len(rows), limit),
            "items": [row.asDict(recursive=True) for row in rows[:limit]],
        }
    except Exception as error:
        return safe_error(error)


report = {
    "inventory_type": "SOMENTE_METADADOS",
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "catalog": CATALOG,
    "schema": SCHEMA,
    "spark_available": spark_session is not None,
    "python_version": platform.python_version(),
    "queries": {},
    "package_versions": {},
    "limits": [
        "Somente objetos visíveis ao usuário que executou o notebook.",
        "Nenhuma linha de dados de negócio foi consultada.",
        "Nenhuma definição de função, descrição, tag ou credencial foi extraída.",
        "Nome do modelo e presença de pacotes não comprovam uso de CausalImpact.",
        "Resultados truncados são identificados; não representam inventário completo.",
    ],
}

# COMMAND ----------

report["queries"]["tables"] = read_metadata(
    f"SHOW TABLES IN {namespace_sql}",
    MAX_OBJECTS,
)

report["queries"]["columns"] = read_metadata(
    f"""
    SELECT table_name, column_name, ordinal_position,
           data_type, full_data_type, is_nullable
    FROM {information_schema_sql}.columns
    WHERE table_catalog = {sql_literal(CATALOG)}
      AND table_schema = {sql_literal(SCHEMA)}
    ORDER BY table_name, ordinal_position
    """,
    MAX_COLUMNS,
)

report["queries"]["volumes"] = read_metadata(
    f"""
    SELECT volume_catalog, volume_schema, volume_name, volume_type
    FROM {information_schema_sql}.volumes
    WHERE volume_catalog = {sql_literal(CATALOG)}
      AND volume_schema = {sql_literal(SCHEMA)}
    ORDER BY volume_name
    """,
    MAX_OBJECTS,
)

report["queries"]["functions"] = read_metadata(
    f"""
    SELECT routine_name, specific_name, routine_type,
           routine_body, data_type, full_data_type
    FROM {information_schema_sql}.routines
    WHERE routine_catalog = {sql_literal(CATALOG)}
      AND routine_schema = {sql_literal(SCHEMA)}
    ORDER BY routine_name, specific_name
    """,
    MAX_OBJECTS,
)

# Recupera o nome completo exibido de forma truncada no print, se estiver visível.
table_names = set()
for row in report["queries"]["tables"].get("items", []):
    name = row.get("tableName") or row.get("table_name")
    if name:
        table_names.add(str(name))
for row in report["queries"]["columns"].get("items", []):
    if row.get("table_name"):
        table_names.add(str(row["table_name"]))

report["gold_campaign_prefix_matches"] = sorted(
    name for name in table_names if name.startswith("gold_campaign_m")
)

# COMMAND ----------

# Consulta metadados das distribuições sem importar TensorFlow ou CausalImpact.
packages = [
    "tfp-causalimpact", "tfcausalimpact", "pycausalimpact", "causalimpact",
    "tensorflow", "tensorflow-cpu", "tensorflow-probability", "tf-keras",
    "mlflow", "mlflow-skinny", "numpy", "pandas",
]

for package in packages:
    try:
        report["package_versions"][package] = {
            "status": "INSTALADO",
            "version": metadata.version(package),
        }
    except metadata.PackageNotFoundError:
        report["package_versions"][package] = {"status": "NAO_ENCONTRADO"}
    except Exception as error:
        report["package_versions"][package] = safe_error(error)

# COMMAND ----------

# Consulta somente o modelo com nome já confirmado.
# Usa o contexto autenticado do próprio Databricks; não solicita tokens/perfis.
# Não chama load_model, predict, funções SQL ou endpoints.
report["registered_model"] = {
    "requested_name": MODEL_NAME,
    "engine_verified_from_source": False,
}

if spark_session is None:
    report["registered_model"].update({
        "status": "NAO_EXECUTADO",
        "motivo": "Execute no notebook Databricks com sessão Spark.",
    })
else:
    try:
        from mlflow import MlflowClient

        registry_client = MlflowClient(registry_uri="databricks-uc")
        model_metadata = registry_client.get_registered_model(MODEL_NAME)
        report["registered_model"].update({
            "status": "OK",
            "name": model_metadata.name,
            "aliases": {
                str(alias): str(version)
                for alias, version in (getattr(model_metadata, "aliases", {}) or {}).items()
            },
        })

        try:
            versions = registry_client.search_model_versions(
                filter_string=f"name = {sql_literal(MODEL_NAME)}",
                max_results=MAX_MODEL_VERSIONS,
            )
            report["registered_model"]["versions"] = {
                "status": "OK",
                "items": [str(version.version) for version in versions],
                "has_more": bool(getattr(versions, "token", None)),
            }
        except Exception as error:
            report["registered_model"]["versions"] = safe_error(error)

    except Exception as error:
        report["registered_model"].update(safe_error(error))

# COMMAND ----------

report["next_artifacts"] = [
    {
        "artifact": "Source ZIP da pasta real do projeto no Workspace",
        "purpose": (
            "Ler os notebooks e arquivos existentes, sua ordem, parâmetros, "
            "origem dos dados e implementação científica."
        ),
    },
    {
        "artifact": "Configuração do Job existente, se houver",
        "purpose": (
            "Identificar tarefas, dependências, parâmetros e ambiente. "
            "Remover segredos e valores sensíveis antes de compartilhar."
        ),
    },
    {
        "artifact": "Definição da função e código que registra bh_counterfactual_model",
        "purpose": (
            "Confirmar algoritmo, pacote, pré/pós, controles e rastreabilidade. "
            "Não é necessário executar nem exportar o modelo binário neste passo."
        ),
    },
    {
        "artifact": "Contrato ou documentação da fonte",
        "purpose": (
            "Identificar data, variável resposta, controles, intervenção, "
            "frequência e regra de atualização; não enviar dados pessoais."
        ),
    },
    {
        "artifact": "Environment ou lista de dependências do notebook científico",
        "purpose": (
            "As versões deste inventário pertencem ao notebook que o executou; "
            "outros notebooks e Jobs podem usar ambientes diferentes."
        ),
    },
]

sections = list(report["queries"].values()) + [report["registered_model"]]
versions_status = report["registered_model"].get("versions", {})
report["inventory_status"] = (
    "METADADOS_COLETADOS"
    if all(section.get("status") == "OK" for section in sections)
    and versions_status.get("status") == "OK"
    and not any(section.get("truncated", False) for section in sections)
    and not versions_status.get("has_more", False)
    else "PARCIAL_OU_PENDENTE"
)
report["interpretation"] = (
    "Este status descreve apenas a coleta de metadados. "
    "Não valida os dados, o modelo, a execução do projeto ou uma conclusão causal."
)

# Única saída explícita: JSON de metadados. Não grava arquivo ou objeto.
print(json.dumps(report, ensure_ascii=False, indent=2))
