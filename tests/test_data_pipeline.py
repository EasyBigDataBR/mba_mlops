"""Contract tests using the delivered ten CSVs, with no cloud dependencies."""

from __future__ import annotations

import copy
import csv
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from data_pipeline import INPUT_COLUMNS, OUTPUT_COLUMNS, canonical_snapshot_bytes, plan_snapshot


class DataPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "data_demo/manifest.json").read_text(encoding="utf-8"))
        cls.names = [entry["filename"] for entry in cls.manifest["files"]]
        cls.payloads = {name: (ROOT / "data_demo" / name).read_bytes() for name in cls.names}

    def supplied(self, count):
        return {name: self.payloads[name] for name in self.names[:count]}

    def event(self, plan, number):
        return next(event for event in plan["events"] if event["filename"] == self.names[number - 1])

    def edited_delivery(self, number, edit):
        """Change bytes AND declared identity to isolate semantic validation."""
        name = self.names[number - 1]
        rows = list(csv.reader(io.StringIO(self.payloads[name].decode())))
        edit(rows)
        stream = io.StringIO(newline="")
        csv.writer(stream, lineterminator="\n").writerows(rows)
        payload = stream.getvalue().encode()
        manifest = copy.deepcopy(self.manifest)
        entry = manifest["files"][number - 1]
        entry["sha256"] = hashlib.sha256(payload).hexdigest()
        entry["byte_count"] = len(payload)
        files = self.supplied(max(5, number))
        files[name] = payload
        return files, manifest

    def test_six_expected_runs_match_manifest_hashes(self):
        for count, expected in zip((5, 6, 7, 8, 9, 10), self.manifest["run_plan"]):
            with self.subTest(files=count):
                plan = plan_snapshot(self.supplied(count), self.manifest)
                self.assertEqual(plan["status"], "BLOCKED" if count == 7 else "READY")
                self.assertEqual(len(plan["data"]), expected["accepted_row_count"])
                self.assertEqual(plan["snapshot_id"], expected["snapshot_sha256"])
                self.assertEqual(plan["as_of"], expected["accepted_as_of"])
                self.assertEqual(plan["summary"]["treated_total"], expected["treated_total"])
                self.assertEqual(plan["summary"]["publishable"], count != 7)
                self.assertEqual(list(plan["data"]), OUTPUT_COLUMNS)
                self.assertFalse(plan["data"].isna().any().any())
                self.assertFalse(plan["data"]["date"].duplicated().any())

    def test_empty_and_contiguous_partial_base_are_incomplete(self):
        for count, rows in ((0, 0), (1, 21), (4, 84)):
            with self.subTest(files=count):
                plan = plan_snapshot(self.supplied(count), self.manifest)
                self.assertEqual(plan["status"], "INCOMPLETE")
                self.assertEqual(len(plan["data"]), rows)
                self.assertFalse(plan["summary"]["publishable"])

    def test_replay_and_dictionary_order_are_idempotent(self):
        files = self.supplied(10)
        before = copy.deepcopy(self.manifest)
        first = plan_snapshot(files, self.manifest)
        second = plan_snapshot(dict(reversed(list(files.items()))), self.manifest)
        self.assertEqual(first["snapshot_id"], second["snapshot_id"])
        self.assertEqual(first["events"], second["events"])
        self.assertEqual(first["summary"], second["summary"])
        pd.testing.assert_frame_equal(first["data"], second["data"])
        self.assertEqual(self.manifest, before)
        self.assertEqual(files, self.supplied(10))

    def test_unknown_csv_blocks_the_cycle(self):
        files = self.supplied(5)
        files["unexpected.csv"] = self.payloads[self.names[0]]
        plan = plan_snapshot(files, self.manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertEqual(len(plan["data"]), 98)
        self.assertIn("UNKNOWN_FILE_NOT_DECLARED_IN_MANIFEST", plan["events"][-1]["errors"])

    def test_changed_bytes_with_same_name_are_rejected(self):
        files = self.supplied(6)
        files[self.names[5]] += b"\n"
        plan = plan_snapshot(files, self.manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn("SHA256_MISMATCH", self.event(plan, 6)["errors"])
        self.assertEqual(len(plan["data"]), 98)

    def test_invalid_seventh_delivery_is_rejected_atomically(self):
        plan = plan_snapshot(self.supplied(7), self.manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertEqual(len(plan["data"]), 105)
        self.assertEqual(self.event(plan, 7)["status"], "REJECTED")
        self.assertTrue(any("control_a:MISSING" in error for error in self.event(plan, 7)["errors"]))
        self.assertNotIn(self.names[6], set(plan["data"]["source_file"]))

    def test_valid_replacement_preserves_original_rejection_evidence(self):
        plan = plan_snapshot(self.supplied(8), self.manifest)
        event = self.event(plan, 7)
        self.assertEqual(plan["status"], "READY")
        self.assertEqual(event["status"], "SUPERSEDED")
        self.assertEqual(event["validation_status"], "REJECTED")
        self.assertEqual(event["superseded_by"], self.names[7])
        self.assertTrue(event["errors"])
        self.assertEqual(sum(plan["data"]["source_file"] == self.names[7]), 7)

    def test_invalid_replacement_does_not_supersede_rejected_original(self):
        files, manifest = self.edited_delivery(8, lambda rows: rows[1].__setitem__(3, ""))
        plan = plan_snapshot(files, manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertEqual(len(plan["data"]), 105)
        self.assertEqual(self.event(plan, 7)["status"], "REJECTED")
        self.assertIsNone(self.event(plan, 7)["superseded_by"])
        self.assertEqual(self.event(plan, 8)["status"], "REJECTED")

    def test_invalid_replacement_does_not_retire_valid_original(self):
        files, manifest = self.edited_delivery(8, lambda rows: rows[1].__setitem__(3, ""))
        files[self.names[6]] = self.payloads[self.names[7]]
        manifest["files"][6]["sha256"] = hashlib.sha256(files[self.names[6]]).hexdigest()
        manifest["files"][6]["byte_count"] = len(files[self.names[6]])
        plan = plan_snapshot(files, manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertEqual(len(plan["data"]), 112)
        self.assertEqual(self.event(plan, 7)["status"], "ACCEPTED")
        self.assertEqual(sum(plan["data"]["source_file"] == self.names[6]), 7)

    def test_unrecognized_historical_bytes_cannot_be_hidden_by_correction(self):
        files = self.supplied(8)
        files[self.names[6]] += b"\n"
        plan = plan_snapshot(files, self.manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertEqual(self.event(plan, 7)["status"], "REJECTED")
        self.assertEqual(self.event(plan, 8)["status"], "REJECTED")
        self.assertIn("CANNOT_SUPERSEDE_UNRECOGNIZED_FILE_BYTES", self.event(plan, 8)["errors"])

    def test_late_correction_replaces_one_key_and_keeps_latest_as_of(self):
        before = plan_snapshot(self.supplied(9), self.manifest)
        after = plan_snapshot(self.supplied(10), self.manifest)
        left = before["data"].set_index("date")
        right = after["data"].set_index("date")
        changed = (left[INPUT_COLUMNS[1:]] != right[INPUT_COLUMNS[1:]]).any(axis=1)
        self.assertEqual(list(changed[changed].index), ["2026-10-26"])
        self.assertEqual(int(right["treated"].sum() - left["treated"].sum()), 12)
        self.assertEqual(after["as_of"], "2026-11-24")
        self.assertEqual(len(right), 119)
        self.assertNotEqual(before["snapshot_id"], after["snapshot_id"])
        self.assertEqual(right.loc["2026-10-26", "source_file"], self.names[9])
        self.assertEqual(right.loc["2026-10-26", "source_revision"], 2)

    def test_late_correction_requires_original_accepted_day(self):
        files = self.supplied(4)
        files[self.names[9]] = self.payloads[self.names[9]]
        plan = plan_snapshot(files, self.manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertTrue(any("CORRECTION_HAS_NO_ACCEPTED_BASE_ROW" in error for error in self.event(plan, 10)["errors"]))
        self.assertEqual(len(plan["data"]), 84)

    def test_lower_or_equal_revision_is_not_applied(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["files"][9]["revision"] = 1
        plan = plan_snapshot(self.supplied(10), manifest)
        before = plan_snapshot(self.supplied(9), self.manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertEqual(plan["snapshot_id"], before["snapshot_id"])
        self.assertTrue(any("HIGHER_REVISION" in error for error in self.event(plan, 10)["errors"]))

    def test_undeclared_correction_date_fails_closed(self):
        manifest = copy.deepcopy(self.manifest)
        manifest["files"][9]["correction_dates"] = ["2026-10-27"]
        plan = plan_snapshot(self.supplied(10), manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertFalse(plan["summary"]["publishable"])

    def test_missing_day_inside_file_is_rejected(self):
        files, manifest = self.edited_delivery(6, lambda rows: rows.pop(3))
        plan = plan_snapshot(files, manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn("DATE_RANGE_OR_DAILY_COVERAGE_MISMATCH", self.event(plan, 6)["errors"])
        self.assertEqual(len(plan["data"]), 98)

    def test_missing_whole_delivery_creates_a_blocking_daily_gap(self):
        files = self.supplied(8)
        del files[self.names[5]]
        plan = plan_snapshot(files, self.manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn("SNAPSHOT_HAS_DAILY_GAPS", plan["summary"]["errors"])
        self.assertEqual(plan["as_of"], "2026-11-03")
        self.assertEqual(len(plan["summary"]["missing_dates"]), 7)

    def test_duplicate_date_inside_file_is_rejected(self):
        files, manifest = self.edited_delivery(6, lambda rows: rows[2].__setitem__(0, rows[1][0]))
        plan = plan_snapshot(files, manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertIn("DUPLICATE_DATE_WITHIN_FILE", self.event(plan, 6)["errors"])

    def test_non_integer_negative_nan_infinite_missing_counts_are_rejected(self):
        for invalid in ("-1", "1.0", "NaN", "inf", "", "1e3", str(2**63), "9" * 5000):
            with self.subTest(value=invalid[:40]):
                files, manifest = self.edited_delivery(6, lambda rows: rows[1].__setitem__(1, invalid))
                plan = plan_snapshot(files, manifest)
                self.assertEqual(plan["status"], "BLOCKED")
                self.assertEqual(self.event(plan, 6)["status"], "REJECTED")

    def test_wrong_schema_or_date_is_rejected(self):
        edits = (
            lambda rows: rows[0].__setitem__(1, "counterfactual"),
            lambda rows: rows[1].__setitem__(0, "04/11/2026"),
            lambda rows: rows[1].__setitem__(0, "2026-11-25"),
        )
        for edit in edits:
            files, manifest = self.edited_delivery(6, edit)
            self.assertEqual(plan_snapshot(files, manifest)["status"], "BLOCKED")

    def test_overlap_requires_explicit_correction(self):
        files = self.supplied(6)
        rows = list(csv.reader(io.StringIO(self.payloads[self.names[4]].decode())))[:8]
        stream = io.StringIO(newline="")
        csv.writer(stream, lineterminator="\n").writerows(rows)
        files[self.names[5]] = stream.getvalue().encode()
        manifest = copy.deepcopy(self.manifest)
        entry = manifest["files"][5]
        entry.update(sha256=hashlib.sha256(files[self.names[5]]).hexdigest(), byte_count=len(files[self.names[5]]), period_start=rows[1][0], period_end=rows[-1][0])
        plan = plan_snapshot(files, manifest)
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertTrue(any("OVERLAP_WITHOUT_DECLARED_CORRECTION" in error for error in self.event(plan, 6)["errors"]))
        self.assertEqual(len(plan["data"]), 98)

    def test_provenance_is_excluded_from_snapshot_identity(self):
        original = plan_snapshot(self.supplied(6), self.manifest)
        manifest = copy.deepcopy(self.manifest)
        manifest["files"][5]["revision"] = 2
        changed = plan_snapshot(self.supplied(6), manifest)
        self.assertEqual(changed["status"], "READY")
        self.assertEqual(original["snapshot_id"], changed["snapshot_id"])
        self.assertFalse(original["data"]["source_revision"].equals(changed["data"]["source_revision"]))
        self.assertEqual(canonical_snapshot_bytes(original["data"]), canonical_snapshot_bytes(changed["data"]))

    def test_manifest_tampering_fails_closed(self):
        for change in (
            lambda m: m["files"][0].__setitem__("sha256", "not-a-hash"),
            lambda m: m["files"][1].__setitem__("filename", m["files"][0]["filename"]),
            lambda m: m.__setitem__("pre_start", "2026-07-30"),
        ):
            manifest = copy.deepcopy(self.manifest)
            change(manifest)
            plan = plan_snapshot(self.supplied(5), manifest)
            self.assertEqual(plan["status"], "BLOCKED")
            self.assertTrue(plan["summary"]["errors"])


if __name__ == "__main__":
    unittest.main()
