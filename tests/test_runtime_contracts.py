"""Regressões locais de retomada e painel, sem Spark/MLflow/Databricks.

Os valores abaixo são fixtures de integridade, não resultados de CausalImpact.
Execute: python -m unittest discover -s tests -p test_runtime_contracts.py -v
"""
from copy import deepcopy
from datetime import date, datetime
import hashlib
from pathlib import Path
import sys
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.databricks_runtime import (  # noqa: E402
    DEFAULTS, DataGateError, describe_source_files, panel_state, source_files_from_rows,
    source_metadata_index, validate_config, verify_effect_rows,
)


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


class SourceDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.filename = "01_base_pre_01.csv"
        self.payload = b"date,treated,control_a,control_b\n2026-07-29,10,20,30\n"
        # ID fictício de fixture: nenhum identificador privado entra no teste.
        self.drive_url = "https://drive.google.com/file/d/DEMO_FILE_A/view?usp=sharing"
        self.row = {"filename": self.filename, "source_path": self.drive_url,
                    "length": len(self.payload), "content": self.payload}

    def receipt(self, name=None, payload=None):
        return {"filename": name or self.filename,
                "sha256": hashlib.sha256(self.payload if payload is None else payload).hexdigest()}

    def test_drive_view_url_uses_selected_filename_metadata(self):
        metadata = source_metadata_index([self.row], 10)
        files, origins = source_files_from_rows([self.row], metadata)
        self.assertEqual(files, {self.filename: self.payload})
        self.assertEqual(origins, {self.filename: self.drive_url})
        self.assertNotIn("view", files)

    def test_filename_metadata_is_not_url_decoded(self):
        row = {**self.row, "filename": "entrega%20literal.csv"}
        files, _ = source_files_from_rows([row], source_metadata_index([row], 10))
        self.assertIn("entrega%20literal.csv", files)
        self.assertNotIn("entrega literal.csv", files)

    def test_volume_path_is_preserved_as_origin(self):
        row = {**self.row, "source_path": "dbfs:/Volumes/mba/mlops_causalimpact/landing/demo/01_base_pre_01.csv"}
        files, origins = source_files_from_rows([row], source_metadata_index([row], 10))
        self.assertEqual(files[self.filename], self.payload)
        self.assertEqual(origins[self.filename], row["source_path"])

    def test_duplicate_names_in_different_drive_files_are_blocked(self):
        second = {**self.row, "source_path": "https://drive.google.com/file/d/DEMO_FILE_B/view"}
        with self.assertRaisesRegex(DataGateError, "Nome de CSV repetido"):
            source_metadata_index([self.row, second], 10)

    def test_duplicate_origin_is_blocked_even_with_different_names(self):
        second = {**self.row, "filename": "02_base_pre_02.csv"}
        with self.assertRaisesRegex(DataGateError, "mesma origem"):
            source_metadata_index([self.row, second], 10)

    def test_missing_filename_never_falls_back_to_url(self):
        missing = {key: value for key, value in self.row.items() if key != "filename"}
        with self.assertRaisesRegex(DataGateError, "Metadados incompletos"):
            source_metadata_index([missing], 10)

    def test_metadata_limits_are_checked_before_content_collection(self):
        for length in (-1, None, True, 1_000_001):
            with self.subTest(length=length), self.assertRaises(DataGateError):
                source_metadata_index([{**self.row, "length": length}], 10)
        rows = [{"filename": f"{i:02d}.csv", "source_path": f"fixture://file/{i}", "length": 900_000}
                for i in range(6)]
        with self.assertRaisesRegex(DataGateError, "5 MB"):
            source_metadata_index(rows, 10)
        with self.assertRaisesRegex(DataGateError, "mais CSVs"):
            source_metadata_index(rows, 5)

    def test_changes_between_metadata_and_content_are_blocked(self):
        metadata = source_metadata_index([self.row], 10)
        cases = [[], [self.row, self.row],
                 [{**self.row, "filename": "renamed.csv"}],
                 [{**self.row, "source_path": "fixture://changed-origin"}],
                 [{**self.row, "length": len(self.payload) + 1}],
                 [{**self.row, "content": self.payload + b"x"}],
                 [{**self.row, "content": None}]]
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(DataGateError):
                source_files_from_rows(rows, metadata)

    def test_first_receipt_is_new_and_validation_remains_separate(self):
        result = describe_source_files({self.filename: self.payload}, {self.filename: self.drive_url}, [])
        self.assertEqual(result["new_file_count"], 1)
        self.assertEqual(result["unchanged_file_count"], 0)
        self.assertEqual(result["read_mode"], "BOUNDED_FULL_READ")
        self.assertEqual(result["comparison_basis"], "BRONZE_FILENAME_SHA256")
        self.assertTrue(result["validation_is_separate"])

    def test_rejected_file_already_in_bronze_is_unchanged_on_retry(self):
        name, payload = "07_append_pos_03_invalido.csv", b"fixture-rejected-by-data-contract"
        known = [self.receipt(name, payload)]
        # Ainda não consta em snapshot aceito, mas seus bytes já foram recebidos.
        result = describe_source_files({name: payload}, {name: self.drive_url}, known, accepted_files={})
        self.assertEqual(result["new_file_count"], 0)
        self.assertEqual(result["unchanged_file_count"], 1)
        self.assertEqual(result["files"][0]["status"], "UNCHANGED")
        self.assertTrue(result["validation_is_separate"])

    def test_added_file_is_new_and_existing_file_is_unchanged(self):
        second = "06_append_pos_02.csv"
        files = {self.filename: self.payload, second: b"next-delivery"}
        origins = {self.filename: self.drive_url, second: "fixture://next-origin"}
        accepted = {self.filename: self.receipt()["sha256"]}
        result = describe_source_files(files, origins, [self.receipt()], accepted)
        self.assertEqual(result["new_file_count"], 1)
        self.assertEqual(result["unchanged_file_count"], 1)
        self.assertEqual({x["filename"]: x["status"] for x in result["files"]},
                         {self.filename: "UNCHANGED", second: "NEW"})

    def test_same_hash_under_new_name_still_identifies_a_new_file(self):
        name = "copy_with_other_name.csv"
        result = describe_source_files({name: self.payload}, {name: "fixture://copy"}, [self.receipt()])
        self.assertEqual(result["files"][0]["status"], "NEW")

    def test_overwriting_accepted_bytes_is_blocked(self):
        accepted = {self.filename: self.receipt()["sha256"]}
        with self.assertRaisesRegex(DataGateError, "alteradas=.*01_base_pre_01.csv"):
            describe_source_files({self.filename: self.payload + b"changed"},
                                  {self.filename: self.drive_url}, [self.receipt()], accepted)

    def test_removing_accepted_file_is_blocked(self):
        accepted = {self.filename: self.receipt()["sha256"]}
        with self.assertRaisesRegex(DataGateError, "Ausentes=.*01_base_pre_01.csv"):
            describe_source_files({}, {}, [self.receipt()], accepted)


class SourceConfigTests(unittest.TestCase):
    def test_default_drive_requires_private_entry_folder_configuration(self):
        self.assertEqual(DEFAULTS["source_mode"], "drive")
        self.assertEqual(DEFAULTS["source_path"], "")
        self.assertEqual(DEFAULTS["drive_connection"], "")
        with self.assertRaisesRegex(ValueError, "subpasta Entrada.*Reserva"):
            validate_config({})

    def test_explicit_drive_configuration_is_accepted(self):
        config = validate_config({"source_mode": "drive",
                                  "source_path": "https://drive.google.com/drive/folders/DEMO_INPUT_FOLDER",
                                  "drive_connection": "demo_drive_connection"})
        self.assertEqual(config["source_mode"], "drive")
        self.assertEqual(config["max_files_per_run"], 10)

    def test_explicit_volume_configuration_still_works(self):
        path = "/Volumes/mba/mlops_causalimpact/landing/causalimpact_demo"
        config = validate_config({"source_mode": "volume", "source_path": path})
        self.assertEqual(config["source_mode"], "volume")
        self.assertEqual(config["source_path"], path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
