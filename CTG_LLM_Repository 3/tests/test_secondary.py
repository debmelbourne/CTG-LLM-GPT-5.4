import unittest
import numpy as np
import pandas as pd

from ctg_llm.secondary import (
    categorize_bmi, categorize_parity, make_four_way_split,
    engineer_features, engineer_external_features, CLINICAL_FEATURES,
)
from ctg_llm.probability_metrics import evaluate_probabilities


class SecondaryTests(unittest.TestCase):
    def feature_frame(self):
        return pd.DataFrame({
            "identifier": ["a", "b"], "asphyxia_pick": [0, 1],
            "Maternal_BMI": [25.0, np.nan], "Parity": [0.0, np.nan],
            "Meconeum": [1, None], "Labour_onset_svsi": [0, 7],
            "Fetal_presention": [1, None], "Maternal_position": [None, "Left"],
            "Fetal_position": [None, "Anterior"], "Regional_anaesthetic": [0, 1],
            "OBS_CODE": [None, "Other"], "FHR1ModeDECGdur": [3.0, np.nan],
            "FHR2ModeDECGdur": [2.0, np.nan], "FHR1ModeUSdur": [4.0, 1.0],
            "FHR2ModeUSdur": [np.nan, 2.0], "ranzcog_label": [1, 4],
            "nichd_label": [0, 2], "rcog_label": [1, 3],
            "parer_label": [2, 5], "figo_label": [1, 3]})

    def test_bmi_boundary_and_missing_categories(self):
        actual = [categorize_bmi(x) for x in [18.49, 18.5, 24.99, 25, 29.99, 30, np.nan]]
        self.assertEqual(actual, ["Underweight", "Normal", "Normal", "Overweight",
                                  "Overweight", "Obese", "Missing"])

    def test_parity_preserves_missing_category(self):
        self.assertEqual([categorize_parity(x) for x in [0, 1, np.nan]],
                         ["Nulliparous", "Multiparous", "Missing"])

    def test_predictor_transformations_and_all_missing_durations(self):
        frame = engineer_features(self.feature_frame())
        self.assertEqual(frame.loc[0, "ECG_Trace_duration"], 5.0)
        self.assertTrue(pd.isna(frame.loc[1, "ECG_Trace_duration"]))
        self.assertEqual(frame.loc[1, "US_Trace_duration"], 3.0)
        self.assertEqual(frame["Labour_onset_svsi"].tolist(), ["Spontaneous", "Unknown"])
        self.assertEqual(frame["Fetal_presention"].tolist(), ["Breech", "Unknown"])
        self.assertEqual(frame["nichd_enc"].tolist(), [1, 3])
        self.assertEqual(frame["parer_enc"].tolist(), [1, 3])

    def test_external_prederived_duration_input(self):
        frame = self.feature_frame().drop(columns=["FHR1ModeDECGdur", "FHR2ModeDECGdur",
                                                  "FHR1ModeUSdur", "FHR2ModeUSdur"])
        frame["ECG_Trace_duration"] = [5.0, 6.0]
        frame["US_Trace_duration"] = [7.0, 8.0]
        result = engineer_external_features(frame)
        self.assertEqual(result["ECG_Trace_duration"].tolist(), [5.0, 6.0])
        self.assertEqual(result["BMI_category"].tolist(), ["Overweight", "Missing"])

    def test_declared_predictors_exclude_outcomes_and_management(self):
        self.assertEqual(len(CLINICAL_FEATURES), 16)
        self.assertFalse({"asphyxia_pick", "Intervened", "Sentinel_SAFC"} & set(CLINICAL_FEATURES))

    def test_partitions_are_disjoint_complete_and_repeatable(self):
        data = pd.DataFrame({"asphyxia_pick": np.tile([0, 1], 481)})
        split = make_four_way_split(data, "asphyxia_pick")
        again = make_four_way_split(data, "asphyxia_pick")
        self.assertEqual([len(split[k]) for k in ("train", "stack", "calibration", "test")],
                         [576, 144, 97, 145])
        combined = np.concatenate(list(split.values()))
        self.assertEqual(len(np.unique(combined)), len(data))
        for key in split:
            np.testing.assert_array_equal(split[key], again[key])
            self.assertEqual(set(data.loc[split[key], "asphyxia_pick"]), {0, 1})

    def test_duplicate_identifiers_cannot_cross_partitions(self):
        data = pd.DataFrame({"identifier": ["duplicate"]*100,
                             "asphyxia_pick": np.tile([0, 1], 50)})
        with self.assertRaises(ValueError):
            make_four_way_split(data, "asphyxia_pick")

    def test_probability_point_estimates(self):
        result = evaluate_probabilities([0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8], reps=20)
        self.assertEqual(result["auroc"], 0.75)
        self.assertAlmostEqual(result["brier_score"], 0.158125)
        self.assertEqual(result["n"], 4)
        self.assertEqual(result["events"], 2)

    def test_paired_identical_predictions_have_zero_auc_difference(self):
        p = [0.1, 0.4, 0.35, 0.8]
        result = evaluate_probabilities([0, 0, 1, 1], p, reference=p, reps=20)
        self.assertEqual([result[k] for k in ("delta_auroc_vs_reference",
                         "delta_auroc_ci_lower", "delta_auroc_ci_upper")], [0.0]*3)

    def test_heldout_and_external_resampling_contracts_differ(self):
        y, p = [0, 0, 1, 1], [0.1, 0.4, 0.35, 0.8]
        heldout = evaluate_probabilities(y, p, stage="heldout", reps=20)
        external = evaluate_probabilities(y, p, stage="external", reps=20)
        self.assertNotIn("brier_ci_lower", heldout)
        self.assertIn("brier_ci_lower", external)
        self.assertIn("calibration_slope_ci_lower", external)
        self.assertEqual(heldout["auroc"], external["auroc"])

    def test_invalid_probability_inputs_are_rejected(self):
        for y, p in [([0, 1], [0.1]), ([0, 1], [0.1, np.nan]),
                     ([0, 1], [0.1, 1.1]), ([0, 0], [0.1, 0.2])]:
            with self.assertRaises(ValueError):
                evaluate_probabilities(y, p, reps=20)


if __name__ == "__main__":
    unittest.main()
