"""Ensaio LOCAL do pacote Google real; não usa Spark nem acessa Databricks.

Execute no ambiente científico fixado:
    python tests/run_causal_validation.py --case initial
    python tests/run_causal_validation.py --case final

O caso initial executa também um placebo no pré e um teste de mascaramento de
y pós. Os arquivos de evidência declaram explicitamente a execução local.
"""
from __future__ import annotations

import argparse
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


def inputs(case):
    manifest = json.loads((ROOT / "data_demo/manifest.json").read_text())
    parts, used = [], []
    for item in manifest["files"]:
        if item["expected_validation"] != "VALID":
            continue
        if case == "initial" and item["batch_number"] > 5:
            continue
        path = ROOT / "data_demo" / item["filename"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"]
        parts.append(pd.read_csv(path))
        used.append(item["filename"])
    # Replay de referência do conjunto válido: a revisão explícita substitui
    # a data anterior. O módulo científico recebe o snapshot já resolvido.
    data = pd.concat(parts, ignore_index=True).drop_duplicates("date", keep="last")
    data = data.sort_values("date").reset_index(drop=True)
    config = {"pre_start": manifest["pre_start"],
              "intervention_date": manifest["intervention_date"],
              "as_of": str(data["date"].max()), "run_placebo": case == "initial"}
    return data, config, used


def verify_result(result):
    json.dumps(result, allow_nan=False)
    post = pd.DataFrame([row for row in result["series"] if row["period"] == "POST"])
    summary = result["summary"]
    np.testing.assert_allclose(post["observed"] - post["counterfactual"], post["effect"], atol=1e-8, rtol=0)
    np.testing.assert_allclose(post["effect"].cumsum(), post["cumulative_effect"], atol=1e-8, rtol=0)
    np.testing.assert_allclose(post.iloc[-1]["cumulative_effect"], summary["cumulative_effect"], atol=1e-8, rtol=0)
    for suffix in ("lower", "upper"):
        np.testing.assert_allclose(post.iloc[-1][f"cumulative_effect_{suffix}"], summary[f"cumulative_effect_{suffix}"], atol=1e-8, rtol=0)
    for name in ("counterfactual", "effect", "cumulative_effect"):
        assert (post[name + "_lower"] <= post[name + "_upper"]).all()
    assert result["engine"]["distribution"] == "tfp-causalimpact"
    assert result["engine"]["api"] == "causalimpact.fit_causalimpact"
    assert result["counts"]["pre_days"] == 84
    assert all(row["cumulative_effect"] is None for row in result["series"] if row["period"] == "PRE")
    return {
        "json_without_nan": True,
        "effect_equals_observed_minus_counterfactual": True,
        "cumulative_mean_equals_sum_of_effects": True,
        "last_cumulative_interval_matches_google_summary": True,
        "intervals_ordered": True,
        "pre_accumulation_is_null": True,
        "cumulative_lower_minus_sum_daily_lower": float(summary["cumulative_effect_lower"] - post["effect_lower"].sum()),
        "cumulative_upper_minus_sum_daily_upper": float(summary["cumulative_effect_upper"] - post["effect_upper"].sum()),
    }


def save(name, payload):
    path = ROOT / "validation" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", choices=("initial", "final"), required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    data, config, filenames = inputs(args.case)
    print(json.dumps({"event": "START", "case": args.case, "rows": len(data), "config": config}), flush=True)
    result = run_causal_analysis(data, config)
    checks = verify_result(result)
    provenance = {
        "execution_environment": "LOCAL Python CPU — não executado no Databricks",
        "data_kind": "SYNTHETIC_DEMONSTRATION",
        "executed_at_utc": datetime.now(timezone.utc).isoformat(),
        "case": args.case, "input_files": filenames,
        "source_sha256": hashlib.sha256((ROOT / "src/causal_model.py").read_bytes()).hexdigest(),
    }
    path = save(f"model_{args.case}.json", {"provenance": provenance, "result": result})
    print(json.dumps({"event": "MODEL_SAVED", "path": str(path), "summary": result["summary"], "timing": result["timing"], "placebo": result["diagnostics"]["placebo"]}, ensure_ascii=False), flush=True)
    if args.case == "initial":
        placebo = result["diagnostics"]["placebo"]
        assert placebo["status"] == "EXECUTED"
        assert placebo["training_days"] == 70 and placebo["holdout_days"] == 14
        assert placebo["as_of"] < config["intervention_date"]
        checks["placebo_uses_only_pre_70_plus_14"] = True

        changed = data.copy(deep=True)
        post_mask = changed["date"] >= config["intervention_date"]
        changed.loc[post_mask, "treated"] += 17
        modified = run_causal_analysis(changed, {**config, "run_placebo": False})
        verify_result(modified)
        original_series, modified_series = pd.DataFrame(result["series"]), pd.DataFrame(modified["series"])
        columns = ["counterfactual", "counterfactual_lower", "counterfactual_upper"]
        max_delta = float(np.abs(original_series[columns].to_numpy() - modified_series[columns].to_numpy()).max())
        np.testing.assert_allclose(original_series[columns], modified_series[columns], atol=1e-8, rtol=0)
        assert result["pre_sha256"] == modified["pre_sha256"]
        assert result["input_sha256"] != modified["input_sha256"]
        np.testing.assert_allclose(modified["summary"]["cumulative_effect"] - result["summary"]["cumulative_effect"], 17 * int(post_mask.sum()), atol=1e-8, rtol=0)
        checks["post_outcome_masking"] = {"passed": True, "post_outcome_added_each_day": 17,
                                          "max_counterfactual_difference": max_delta,
                                          "expected_cumulative_effect_difference": 17 * int(post_mask.sum())}
        save("model_post_outcome_masking.json", {"provenance": {**provenance, "case": "post_outcome_masking"}, "result": modified})
    report = {"status": "PASS", "provenance": provenance, "checks": checks,
              "dependencies": result["dependencies"], "elapsed_seconds": time.perf_counter() - start}
    report_path = save(f"model_{args.case}_validation.json", report)
    print(json.dumps({"event": "VALIDATION_PASS", "report": str(report_path), "checks": checks, "elapsed_seconds": report["elapsed_seconds"]}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
