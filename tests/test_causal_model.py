"""Contratos e identidade do estudo; não substituem o ensaio do modelo real.

    python -m unittest discover -s tests -p test_causal_model.py -v
"""
from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.causal_model import (  # noqa: E402
    DataContractError, _data_hash, normalize_config, prepare_inputs,
)


class ModelContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        files = sorted((ROOT / "data_demo").glob("*.csv"))
        cls.files = files
        cls.initial = pd.concat([pd.read_csv(path) for path in files[:5]], ignore_index=True)
        cls.config = {"pre_start": "2026-07-29", "intervention_date": "2026-10-21", "as_of": "2026-11-03"}

    def test_initial_contract_and_fixed_pre(self):
        data, config = prepare_inputs(self.initial, self.config)
        self.assertEqual(len(data), 98)
        self.assertEqual((data.index < pd.Timestamp(config["intervention_date"])).sum(), 84)
        self.assertEqual(config["num_results"], 300)
        self.assertEqual(config["num_warmup_steps"], 100)
        self.assertFalse(config["run_placebo"])

    def test_input_not_modified_and_metadata_not_used(self):
        incoming = self.initial.copy(deep=True)
        incoming["source_file"] = "metadado; nunca é controle"
        before = incoming.copy(deep=True)
        prepared, _ = prepare_inputs(incoming, self.config)
        pd.testing.assert_frame_equal(incoming, before)
        self.assertEqual(list(prepared.columns), ["treated", "control_a", "control_b"])

    def test_reordering_cannot_change_data_identity(self):
        canonical, _ = prepare_inputs(self.initial, self.config)
        shuffled, _ = prepare_inputs(self.initial.sample(frac=1, random_state=7), self.config)
        self.assertEqual(_data_hash(canonical), _data_hash(shuffled))

    def test_duplicate_dates_are_not_summed(self):
        with self.assertRaisesRegex(DataContractError, "mais de uma"):
            prepare_inputs(pd.concat([self.initial, self.initial.iloc[[0]]]), self.config)

    def test_missing_day_is_not_imputed(self):
        with self.assertRaisesRegex(DataContractError, "1 dias ausentes"):
            prepare_inputs(self.initial.drop(index=27), self.config)

    def test_outside_cut_not_silently_removed(self):
        extra = self.initial.iloc[[0]].copy()
        extra["date"] = "2026-07-28"
        with self.assertRaisesRegex(DataContractError, "1 dias fora"):
            prepare_inputs(pd.concat([self.initial, extra]), self.config)

    def test_invalid_counts_block_fit(self):
        for column in ("treated", "control_a", "control_b"):
            for value in (np.nan, np.inf, -1.0, 4.5):
                with self.subTest(column=column, value=value):
                    incoming = self.initial.copy().astype({column: float})
                    incoming.loc[33, column] = value
                    with self.assertRaises(DataContractError):
                        prepare_inputs(incoming, self.config)
        incoming = self.initial.copy()
        incoming["control_a"] = True
        with self.assertRaises(DataContractError):
            prepare_inputs(incoming, self.config)

    def test_date_time_timezone_and_null_rejected(self):
        for value in (None, "2026-08-31T15:30:00", "2026-08-31T00:00:00Z", "invalid-date"):
            with self.subTest(value=value):
                incoming = self.initial.copy()
                incoming.loc[33, "date"] = value
                with self.assertRaises(DataContractError):
                    prepare_inputs(incoming, self.config)

    def test_missing_or_duplicate_column_rejected(self):
        with self.assertRaises(DataContractError):
            prepare_inputs(self.initial.drop(columns="control_b"), self.config)
        duplicated = pd.concat([self.initial, self.initial[["control_b"]]], axis=1)
        with self.assertRaises(DataContractError):
            prepare_inputs(duplicated, self.config)

    def test_zero_variance_pre_rejected(self):
        incoming = self.initial.copy()
        incoming.loc[incoming["date"] < self.config["intervention_date"], "control_b"] = 100
        with self.assertRaisesRegex(DataContractError, "não varia no pré"):
            prepare_inputs(incoming, self.config)

    def test_window_cannot_be_selected_to_fit_observed_effect(self):
        for changes in ({"intervention_date": "2026-10-22"}, {"as_of": "2026-11-02"}, {"pre_start": "2026-7-29"}):
            with self.subTest(changes=changes), self.assertRaises(DataContractError):
                normalize_config({**self.config, **changes})

    def test_unknown_pipeline_config_does_not_silently_change_model(self):
        with self.assertRaisesRegex(DataContractError, "desconhecidos"):
            normalize_config({**self.config, "catalog": "mba"})
        for changes in ({"alpha": float("nan")}, {"weekly_seasonality": "True"}, {"num_results": 1}, {"seed": [-1, 42]}):
            with self.subTest(changes=changes), self.assertRaises(DataContractError):
                normalize_config({**self.config, **changes})

    def test_deliberately_invalid_batch_seven_cannot_reach_model(self):
        data = pd.concat([pd.read_csv(path) for path in self.files[:7]], ignore_index=True)
        with self.assertRaisesRegex(DataContractError, "control_a"):
            prepare_inputs(data, {**self.config, "as_of": str(data["date"].max())})

    def test_late_correction_changes_snapshot_but_not_pre(self):
        original, _ = prepare_inputs(self.initial, self.config)
        corrected_input = pd.concat([self.initial, pd.read_csv(self.files[9])], ignore_index=True).drop_duplicates("date", keep="last")
        corrected, _ = prepare_inputs(corrected_input, self.config)
        self.assertEqual(len(original), len(corrected))
        self.assertNotEqual(_data_hash(original), _data_hash(corrected))
        pre = original.index < pd.Timestamp(self.config["intervention_date"])
        self.assertEqual(_data_hash(original.loc[pre]), _data_hash(corrected.loc[pre]))
        self.assertEqual(float((corrected["treated"] - original["treated"]).sum()), 12)

    def test_final_replay_preserves_entire_pre(self):
        accepted = [path for i, path in enumerate(self.files, start=1) if i != 7]
        final = pd.concat([pd.read_csv(path) for path in accepted], ignore_index=True).drop_duplicates("date", keep="last")
        final_prepared, _ = prepare_inputs(final, {**self.config, "as_of": "2026-11-24"})
        original, _ = prepare_inputs(self.initial, self.config)
        self.assertEqual(len(final_prepared), 119)
        pd.testing.assert_frame_equal(original.iloc[:84], final_prepared.iloc[:84])


if __name__ == "__main__":
    unittest.main(verbosity=2)
