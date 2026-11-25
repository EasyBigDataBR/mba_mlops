"""Reproduz LOCALMENTE os cinco ajustes válidos da demonstração sintética.

    python scripts/run_model_sequence.py

Não acessa Spark/Databricks, não publica runs e não é o orquestrador da nuvem.
Acumula os bytes dos CSVs e chama o mesmo plan_snapshot do runtime em cada ciclo.
O manifest define a ordem de entrega; o gate real decide se há ajuste. Não usa
instructor_truth no modelo.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.causal_model import run_causal_analysis  # noqa: E402
from src.data_pipeline import canonical_snapshot_bytes, plan_snapshot  # noqa: E402


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def main():
    started = time.perf_counter()
    manifest_path = ROOT / "data_demo/manifest.json"
    manifest = json.loads(manifest_path.read_text())
    files = {}
    state = None
    valid_states, rejected, detailed, cycles = [], [], [], []
    supersession_preserved = False
    source_hash = hashlib.sha256((ROOT / "src/causal_model.py").read_bytes()).hexdigest()
    provenance = {
        "execution_environment": "LOCAL Python CPU; não executado no Databricks",
        "data_kind": "SYNTHETIC_DEMONSTRATION",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_sha256": source_hash,
        "data_pipeline_sha256": hashlib.sha256((ROOT / "src/data_pipeline.py").read_bytes()).hexdigest(),
        "sequence_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    for step in manifest["run_plan"]:
        for name in step["deliver_files"]:
            path = ROOT / "data_demo" / name
            payload = path.read_bytes()
            if name in files and files[name] != payload:
                raise AssertionError("Uma entrega já recebida não pode ser sobrescrita.")
            files[name] = payload

        plan = plan_snapshot(files, manifest)
        canonical_hash = hashlib.sha256(canonical_snapshot_bytes(plan["data"])).hexdigest()
        assert canonical_hash == plan["snapshot_id"] == step["snapshot_sha256"]
        cycle = {"run_number": step["run_number"], "new_files": step["deliver_files"],
                 "supplied_file_count": len(files), "status": plan["status"],
                 "snapshot_id": plan["snapshot_id"], "as_of": plan["as_of"],
                 "candidate_rows": len(plan["data"])}
        cycles.append(cycle)
        if plan["status"] != "READY":
            rejected_events = [event for event in plan["events"] if event["status"] == "REJECTED"]
            if state is not None:
                previous_hash = hashlib.sha256(canonical_snapshot_bytes(state)).hexdigest()
                assert previous_hash == plan["snapshot_id"]
            rejected.append({"run_number": step["run_number"], "files": step["deliver_files"],
                             "local_contract_status": plan["status"],
                             "rejected_events": rejected_events, "pipeline_summary": plan["summary"],
                             "candidate_snapshot_id": plan["snapshot_id"],
                             "preserved_snapshot_id": valid_states[-1]["snapshot_id"] if valid_states else None,
                             "preserved_rows": len(state) if state is not None else 0,
                             "preserved_as_of": str(state["date"].max()) if state is not None else None,
                             "new_analysis": False})
            print(json.dumps({"event": "LOCAL_PIPELINE_BLOCKED", **rejected[-1]}, ensure_ascii=False), flush=True)
            continue

        proposed = plan["data"].copy(deep=True)
        config = {"pre_start": manifest["pre_start"], "intervention_date": manifest["intervention_date"],
                  "as_of": plan["as_of"], "run_placebo": False}
        assert len(proposed) == step["accepted_row_count"]
        assert config["as_of"] == step["accepted_as_of"]
        for event in plan["events"]:
            if event["filename"] == "07_append_pos_03_invalido.csv" and event["status"] == "SUPERSEDED":
                assert event["validation_status"] == "REJECTED" and event["errors"]
                assert event["superseded_by"] == "08_correction_pos_03.csv"
                supersession_preserved = True
        print(json.dumps({"event": "LOCAL_FIT_START", "run_number": step["run_number"],
                          "rows": len(proposed), "as_of": config["as_of"]}), flush=True)
        result = run_causal_analysis(proposed, config)
        state = proposed
        if detailed:
            assert result["pre_sha256"] == detailed[0]["pre_sha256"]
            assert result["analysis_config_hash"] == detailed[0]["analysis_config_hash"]
        assert result["input_sha256"] not in {row["input_sha256"] for row in detailed}
        detailed.append(result)
        relative_path = f"validation/sequence/run_{step['run_number']:02d}.json"
        write_json(ROOT / relative_path, {"provenance": provenance,
                   "pipeline": {**cycle, "events": plan["events"], "summary": plan["summary"]}, "result": result})
        state_record = {
            "run_number": step["run_number"], "new_files": step["deliver_files"],
            "as_of": config["as_of"], "counts": result["counts"],
            "snapshot_id": plan["snapshot_id"], "pipeline_status": plan["status"],
            "input_sha256": result["input_sha256"], "pre_sha256": result["pre_sha256"],
            "analysis_config_hash": result["analysis_config_hash"], "analysis_key": result["analysis_key"],
            "summary": result["summary"], "pre_in_sample_mae": result["diagnostics"]["pre_in_sample_mae"],
            "fit_seconds": result["timing"]["main_fit_seconds"], "detailed_result": relative_path,
        }
        valid_states.append(state_record)
        print(json.dumps({"event": "LOCAL_FIT_DONE", "run_number": step["run_number"],
                          "summary": result["summary"]}, ensure_ascii=False), flush=True)

    assert len(valid_states) == 5 and len(rejected) == 1
    assert [cycle["status"] for cycle in cycles] == ["READY", "READY", "BLOCKED", "READY", "READY", "READY"]
    assert rejected[0]["preserved_rows"] == 105 and not rejected[0]["new_analysis"]
    assert supersession_preserved
    before, after = detailed[-2:]
    # O arquivo10 altera apenas y pós em +12; mesma data, controles e seed.
    columns = ["counterfactual", "counterfactual_lower", "counterfactual_upper"]
    a, b = pd.DataFrame(before["series"]), pd.DataFrame(after["series"])
    np.testing.assert_allclose(a[columns], b[columns], atol=1e-8, rtol=0)
    np.testing.assert_allclose(after["summary"]["cumulative_effect"] - before["summary"]["cumulative_effect"], 12, atol=1e-8, rtol=0)
    assert before["counts"] == after["counts"]
    report = {
        "status": "PASS", "provenance": provenance,
        "engine": detailed[0]["engine"], "dependencies": detailed[0]["dependencies"],
        "config": detailed[0]["config"],
        "config_note": "Datas pré/intervenção e parâmetros fixos; as_of de cada estado aparece em valid_states.",
        "valid_states": valid_states, "pipeline_cycles": cycles, "rejected_local_contract": rejected,
        "checks": {"five_real_google_fits": True, "all_pre_fingerprints_equal": True,
                   "all_analysis_config_hashes_equal": True, "five_distinct_input_hashes": True,
                   "same_plan_snapshot_as_databricks_runtime": True,
                   "canonical_snapshot_hashes_match_manifest": True,
                   "invalid_file_rejected_before_fit": True,
                   "invalid_file_keeps_previous_snapshot": True,
                   "supersession_retains_original_rejection": True,
                   "late_correction_same_rows_and_counterfactual": True,
                   "late_correction_cumulative_effect_delta": 12.0},
        "interpretation": [
            "Os primeiros cortes têm horizontes pós diferentes: não compare acumulados como se medissem o mesmo período.",
            "Controles pós participam do prior padrão Google; ampliar o corte pode revisar estimativas no intervalo comum.",
            "O efeito é condicionado às hipóteses do modelo e aos controles; significância não aprova a campanha.",
            "Rejeição local do contrato não demonstra a criação de quarentena/tabelas no Databricks.",
        ],
        "elapsed_seconds": time.perf_counter() - started,
    }
    write_json(ROOT / "validation/local_results.json", report)
    print(json.dumps({"event": "SEQUENCE_PASS", "valid_states": len(valid_states),
                      "rejected_files": len(rejected), "elapsed_seconds": report["elapsed_seconds"]}), flush=True)


if __name__ == "__main__":
    main()
