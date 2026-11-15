import unittest

import numpy as np
import pandas as pd

from ctg_llm.rendering import (
    RenderSettings,
    clean_fhr,
    interpolate_fhr_segments,
    safe_output_stem,
    time_from_trace_end_minutes,
)


class RenderingTests(unittest.TestCase):
    def test_time_axis_is_anchored_to_trace_end(self):
        axis = time_from_trace_end_minutes(5, 250.0)
        self.assertAlmostEqual(axis[-1], 0.0)
        self.assertAlmostEqual(axis[0], -1.0 / 60.0)

    def test_fhr_bounds_and_jump_screen_are_fail_closed(self):
        values = pd.Series([120.0, 121.0, 170.0, 122.0, 220.0])
        cleaned = clean_fhr(values)
        self.assertTrue(pd.isna(cleaned.iloc[1:]).all())
        self.assertEqual(cleaned.iloc[0], 120.0)

    def test_interpolation_does_not_bridge_missing_gap(self):
        values = pd.Series(
            [120.0, 121.0, 122.0, 123.0, 124.0, np.nan,
             130.0, 131.0, 132.0, 133.0, 134.0]
        )
        result = interpolate_fhr_segments(values, min_len_samples=5)
        self.assertTrue(pd.isna(result.iloc[5]))
        self.assertEqual(int(result.notna().sum()), 10)

    def test_settings_and_output_names_are_validated(self):
        self.assertEqual(safe_output_stem("record 001"), "record_001")
        with self.assertRaises(ValueError):
            RenderSettings(window_minutes=0).validate()

if __name__ == "__main__":
    unittest.main()
