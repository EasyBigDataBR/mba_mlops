"""Regressões locais de retomada e painel, sem Spark/MLflow/Databricks.

Os valores abaixo são fixtures de integridade, não resultados de CausalImpact.
Execute: python -m unittest discover -s tests -p test_runtime_contracts.py -v
"""
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.databricks_runtime import panel_state, verify_effect_rows  # noqa: E402


def effect_fixture():
    return [
        {"date": "2026-10-20", "period": "PRE", "observed": 100.0,
         "counterfactual": 101.0, "counterfactual_lower": 91.0, "counterfactual_upper": 111.0,
         "effect": -1.0, "effect_lower": -11.0, "effect_upper": 9.0,
         "cumulative_effect": None, "cumulative_effect_lower": None, "cumulative_effect_upper": None},
        {"date": "2026-10-21", "period": "POST", "observed": 140.0,
         "counterfactual": 105.0, "counterfactual_lower": 95.0, "counterfactual_upper": 115.0,
         "effect": 35.0, "effect_lower": 25.0, "effect_upper": 45.0,
         "cumulative_effect": 35.0, "cumulative_effect_lower": 25.0, "cumulative_effect_upper": 45.0},
        {"date": "2026-10-22", "period": "POST", "observed": 141.0,
         "counterfactual": 106.0, "counterfactual_lower": 96.0, "counterfactual_upper": 116.0,
         "effect": 35.0, "effect_lower": 25.0, "effect_upper": 45.0,
         "cumulative_effect": 70.0, "cumulative_effect_lower": 57.0, "cumulative_effect_upper": 83.0},
    ]


class PersistedEffectsTests(unittest.TestCase):
    def setUp(self):
        self.expected = effect_fixture()

    def test_pandas_dates_nulls_and_reordered_rows_match(self):
        saved = pd.DataFrame(deepcopy(self.expected)).iloc[::-1].copy()
        saved["date"] = saved["date"].map(date.fromisoformat)
        saved["analysis_id"] = "metadata_only"
        self.assertTrue(pd.isna(saved.iloc[-1]["cumulative_effect"]))
        verify_effect_rows(saved, self.expected)

    def test_wrong_interval_blocked_with_same_count_and_last_mean(self):
        saved = deepcopy(self.expected)
        saved[1]["cumulative_effect_upper"] += 2.0
        self.assertEqual(len(saved), len(self.expected))
        self.assertEqual(saved[-1]["cumulative_effect"], self.expected[-1]["cumulative_effect"])
        with self.assertRaisesRegex(RuntimeError, "2026-10-21/cumulative_effect_upper"):
            verify_effect_rows(saved, self.expected)

    def test_each_output_value_is_checked_before_publish(self):
        for column in ("observed", "counterfactual", "counterfactual_lower", "counterfactual_upper",
                       "effect", "effect_lower", "effect_upper", "cumulative_effect",
                       "cumulative_effect_lower", "cumulative_effect_upper"):
            with self.subTest(column=column):
                saved = deepcopy(self.expected)
                saved[1][column] += 1.0
                with self.assertRaisesRegex(RuntimeError, column):
                    verify_effect_rows(saved, self.expected)

    def test_missing_duplicate_or_replaced_day_is_blocked(self):
        duplicate = deepcopy(self.expected)
        duplicate[1]["date"] = duplicate[0]["date"]
        replaced = deepcopy(self.expected)
        replaced[1]["date"] = "2026-10-23"
        for saved in (self.expected[:-1], duplicate, replaced):
            with self.subTest(dates=[r["date"] for r in saved]):
                with self.assertRaisesRegex(RuntimeError, "Datas/contagem"):
                    verify_effect_rows(saved, self.expected)

    def test_period_is_part_of_integrity_check(self):
        saved = deepcopy(self.expected)
        saved[1]["period"] = "PRE"
        with self.assertRaisesRegex(RuntimeError, "Período divergente"):
            verify_effect_rows(saved, self.expected)

    def test_null_is_allowed_only_when_expected(self):
        for row, column, replacement in ((1, "effect", None), (0, "cumulative_effect", 0.0)):
            with self.subTest(row=row, column=column):
                saved = deepcopy(self.expected)
                saved[row][column] = replacement
                with self.assertRaisesRegex(RuntimeError, column):
                    verify_effect_rows(saved, self.expected)

    def test_small_rounding_is_allowed_but_material_change_is_blocked(self):
        saved = deepcopy(self.expected)
        saved[1]["effect"] += 5e-10
        verify_effect_rows(saved, self.expected)
        saved[1]["effect"] += 1e-3
        with self.assertRaisesRegex(RuntimeError, "effect"):
            verify_effect_rows(saved, self.expected)


class PanelStateTests(unittest.TestCase):
    def setUp(self):
        self.ingest = {"status": "READY", "attempt_id": "attempt_new", "snapshot_id": "snapshot_current"}
        self.model_attempt = {"status": "SUCCESS", "attempt_id": "attempt_new",
                              "analysis_id": "analysis_current", "snapshot_id": "snapshot_current"}
        self.selected = {"analysis_id": "analysis_current", "snapshot_id": "snapshot_current",
                         "committed_at": datetime(2026, 11, 25, 10)}

    def test_matching_success_is_consistent(self):
        self.assertEqual(panel_state(self.ingest, self.model_attempt, self.selected), "CONSISTENT")

    def test_analysis_error_same_snapshot_preserves_previous_label(self):
        failed = {**self.model_attempt, "status": "ERROR"}
        self.assertEqual(panel_state(self.ingest, failed, self.selected), "PREVIOUS_VALID_RESULT")

    def test_new_ingestion_same_snapshot_waits_for_its_own_analysis(self):
        previous_model_attempt = {**self.model_attempt, "attempt_id": "attempt_previous"}
        self.assertEqual(panel_state(self.ingest, previous_model_attempt, self.selected), "PREVIOUS_VALID_RESULT")

    def test_no_change_reuses_old_cut_even_with_older_commit_timestamp(self):
        ingest = {"status": "REUSED", "attempt_id": "attempt_replay", "snapshot_id": "snapshot_old"}
        model_attempt = {"status": "NO_CHANGE", "attempt_id": "attempt_replay",
                         "analysis_id": "analysis_old", "snapshot_id": "snapshot_old"}
        selected = {"analysis_id": "analysis_old", "snapshot_id": "snapshot_old",
                    "committed_at": datetime(2026, 11, 3, 10)}
        self.assertEqual(panel_state(ingest, model_attempt, selected), "CONSISTENT")
        # Selecionar a análise global mais recente reproduziria o bug anterior.
        self.assertEqual(panel_state(ingest, model_attempt, self.selected), "PREVIOUS_VALID_RESULT")

    def test_wrong_analysis_id_same_snapshot_is_not_consistent(self):
        different_analysis = {**self.selected, "analysis_id": "analysis_previous_config"}
        self.assertEqual(panel_state(self.ingest, self.model_attempt, different_analysis), "PREVIOUS_VALID_RESULT")

    def test_blocked_or_missing_stage_does_not_approve_previous_result(self):
        cases = [
            ({**self.ingest, "status": "BLOCKED"}, self.model_attempt),
            ({**self.ingest, "status": "REJECTED"}, self.model_attempt),
            (self.ingest, None),
            (None, self.model_attempt),
        ]
        for ingest, model in cases:
            with self.subTest(ingest=ingest, model=model):
                self.assertEqual(panel_state(ingest, model, self.selected), "PREVIOUS_VALID_RESULT")

    def test_no_analysis_is_explicit(self):
        self.assertEqual(panel_state(self.ingest, self.model_attempt, None), "NO_ANALYSIS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
