"""Predictor preparation and four-part partitioning from the study scripts.

This module exposes the recorded-variable transformations and split procedure.
Fitted learners and model-combination components are described separately.
"""
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from .categories import OUTCOME



SEED = 42

TRAIN_FRACTION = 0.60

STACK_FRACTION = 0.15

FINAL_CALIBRATION_FRACTION = 0.10

TEST_FRACTION = 0.15

LABEL_SPECS = {
    "RANZCOG": {
        "raw": "ranzcog_label",
        "encoded": "ranzcog_enc",
        "mapping": {1: 1, 2: 2, 3: 2, 4: 3},
    },
    "NICHD": {
        "raw": "nichd_label",
        "encoded": "nichd_enc",
        "mapping": {0: 1, 1: 2, 2: 3},
    },
    "Parer-Ikeda": {
        "raw": "parer_label",
        "encoded": "parer_enc",
        "mapping": {1: 1, 2: 1, 3: 2, 4: 3, 5: 3},
    },
    "FIGO": {
        "raw": "figo_label",
        "encoded": "figo_enc",
        "mapping": {1: 1, 2: 2, 3: 3},
    },
    "NICE/RCOG": {
        "raw": "rcog_label",
        "encoded": "rcog_enc",
        "mapping": {1: 1, 2: 2, 3: 3},
    },
}

CLINICAL_FEATURES = [
    "Gestation",
    "Maternal_age",
    "Duration_of_labour_1",
    "Duration_of_labour_2",
    "Duration_stage_total",
    "ECG_Trace_duration",
    "US_Trace_duration",
    "Meconeum",
    "Labour_onset_svsi",
    "Fetal_presention",
    "Maternal_position",
    "Fetal_position",
    "Regional_anaesthetic",
    "OBS_CODE",
    "BMI_category",
    "Parity_binary",
]

CLINICAL_CATEGORICAL = [
    "Meconeum",
    "Labour_onset_svsi",
    "Fetal_presention",
    "Maternal_position",
    "Fetal_position",
    "Regional_anaesthetic",
    "OBS_CODE",
    "BMI_category",
    "Parity_binary",
]

def categorize_bmi(value):
    if pd.isna(value):
        return "Missing"
    value = float(value)
    if value < 18.5:
        return "Underweight"
    if value < 25:
        return "Normal"
    if value < 30:
        return "Overweight"
    return "Obese"

def categorize_parity(value):
    if pd.isna(value):
        return "Missing"
    return "Nulliparous" if float(value) == 0 else "Multiparous"

def safe_string(series):
    return series.astype("string").fillna("Missing").astype(str)

def map_guideline_column(series, mapping, column_name):
    numeric = pd.to_numeric(series, errors="coerce")
    unexpected = sorted(set(numeric.dropna().unique()) - set(mapping))
    if unexpected:
        raise ValueError(f"{column_name} contains unexpected values: {unexpected}")
    encoded = numeric.map(mapping)
    failed = numeric.notna() & encoded.isna()
    if failed.any():
        raise ValueError(f"{column_name} contains values that were not encoded.")
    return encoded.astype("Int64")

def engineer_features(data):
    data = data.copy()

    if "identifier" in data.columns:
        data["identifier"] = data["identifier"].astype("string")

    data["BMI_category"] = data["Maternal_BMI"].apply(categorize_bmi).astype(str)
    data["Parity_binary"] = data["Parity"].apply(categorize_parity).astype(str)

    data["Meconeum"] = safe_string(data["Meconeum"])

    labour_numeric = pd.to_numeric(data["Labour_onset_svsi"], errors="coerce")
    data["Labour_onset_svsi"] = (
        labour_numeric.map({0: "Spontaneous", 1: "Induced"})
        .fillna("Unknown")
        .astype(str)
    )

    presentation_numeric = pd.to_numeric(data["Fetal_presention"], errors="coerce")
    data["Fetal_presention"] = (
        presentation_numeric.map({0: "Cephalic", 1: "Breech"})
        .fillna("Unknown")
        .astype(str)
    )

    for column in [
        "Maternal_position",
        "Fetal_position",
        "Regional_anaesthetic",
        "OBS_CODE",
    ]:
        data[column] = safe_string(data[column])

    data["ECG_Trace_duration"] = data[
        ["FHR1ModeDECGdur", "FHR2ModeDECGdur"]
    ].sum(axis=1, min_count=1)
    data["US_Trace_duration"] = data[
        ["FHR1ModeUSdur", "FHR2ModeUSdur"]
    ].sum(axis=1, min_count=1)

    for scheme_name, spec in LABEL_SPECS.items():
        if spec["raw"] in data.columns:
            data[spec["encoded"]] = map_guideline_column(
                data[spec["raw"]], spec["mapping"], spec["raw"]
            )

    return data

def make_four_way_split(data, outcome, seed=SEED):
    if not data.index.is_unique:
        raise ValueError("Partitioning requires a unique row index")
    if "identifier" in data and (data["identifier"].isna().any() or data["identifier"].duplicated().any()):
        raise ValueError("Partitioning requires unique, non-missing study identifiers")
    if data[outcome].isna().any() or set(data[outcome].unique()) != {0, 1}:
        raise ValueError("Partitioning requires both binary outcome classes")
    indices = data.index.to_numpy()
    y = data[outcome]

    remaining_idx, test_idx = train_test_split(
        indices,
        test_size=TEST_FRACTION,
        stratify=y.loc[indices],
        random_state=seed,
    )

    calibration_share_of_remaining = FINAL_CALIBRATION_FRACTION / (
        1.0 - TEST_FRACTION
    )
    train_stack_idx, calibration_idx = train_test_split(
        remaining_idx,
        test_size=calibration_share_of_remaining,
        stratify=y.loc[remaining_idx],
        random_state=seed + 1,
    )

    stack_share_of_train_stack = STACK_FRACTION / (
        TRAIN_FRACTION + STACK_FRACTION
    )
    train_idx, stack_idx = train_test_split(
        train_stack_idx,
        test_size=stack_share_of_train_stack,
        stratify=y.loc[train_stack_idx],
        random_state=seed + 2,
    )

    split_indices = {
        "train": np.asarray(train_idx),
        "stack": np.asarray(stack_idx),
        "calibration": np.asarray(calibration_idx),
        "test": np.asarray(test_idx),
    }

    sets = {name: set(values.tolist()) for name, values in split_indices.items()}
    names = list(sets)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            if sets[left].intersection(sets[right]):
                raise RuntimeError(f"Split overlap detected: {left} and {right}")

    union = set().union(*sets.values())
    if union != set(indices.tolist()):
        raise RuntimeError("Split assignments do not cover the full cohort.")

    return split_indices

def make_model_frame(data, features, categorical_features):
    frame = data.loc[:, features].copy()
    categorical_set = set(categorical_features)
    for column in features:
        if column in categorical_set:
            frame[column] = safe_string(frame[column])
        else:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame

def derive_or_preserve_trace_duration(
    data,
    source_columns,
    derived_column,
):
    if all(column in data.columns for column in source_columns):
        data[derived_column] = data[source_columns].sum(
            axis=1,
            min_count=1,
        )
    elif derived_column in data.columns:
        data[derived_column] = pd.to_numeric(
            data[derived_column],
            errors="coerce",
        )
    else:
        raise KeyError(
            f"Cannot construct {derived_column}; neither the derived column "
            f"nor all source columns {source_columns} are present."
        )

def engineer_external_features(data):
    data = data.copy()

    required_raw_columns = [
        OUTCOME,
        "Maternal_BMI",
        "Parity",
        "Meconeum",
        "Labour_onset_svsi",
        "Fetal_presention",
        "Maternal_position",
        "Fetal_position",
        "Regional_anaesthetic",
        "OBS_CODE",
        *[spec["raw"] for spec in LABEL_SPECS.values()],
    ]
    missing = [
        column
        for column in required_raw_columns
        if column not in data.columns
    ]
    if missing:
        raise KeyError(
            "The CTU workbook is missing required columns: "
            f"{missing}"
        )

    data["BMI_category"] = (
        data["Maternal_BMI"].apply(categorize_bmi).astype(str)
    )
    data["Parity_binary"] = (
        data["Parity"].apply(categorize_parity).astype(str)
    )
    data["Meconeum"] = safe_string(data["Meconeum"])

    labour_numeric = pd.to_numeric(
        data["Labour_onset_svsi"],
        errors="coerce",
    )
    data["Labour_onset_svsi"] = (
        labour_numeric.map({0: "Spontaneous", 1: "Induced"})
        .fillna("Unknown")
        .astype(str)
    )

    presentation_numeric = pd.to_numeric(
        data["Fetal_presention"],
        errors="coerce",
    )
    data["Fetal_presention"] = (
        presentation_numeric.map({0: "Cephalic", 1: "Breech"})
        .fillna("Unknown")
        .astype(str)
    )

    for column in [
        "Maternal_position",
        "Fetal_position",
        "Regional_anaesthetic",
        "OBS_CODE",
    ]:
        data[column] = safe_string(data[column])

    derive_or_preserve_trace_duration(
        data,
        ["FHR1ModeDECGdur", "FHR2ModeDECGdur"],
        "ECG_Trace_duration",
    )
    derive_or_preserve_trace_duration(
        data,
        ["FHR1ModeUSdur", "FHR2ModeUSdur"],
        "US_Trace_duration",
    )

    for spec in LABEL_SPECS.values():
        data[spec["encoded"]] = map_guideline_column(
            data[spec["raw"]],
            spec["mapping"],
            spec["raw"],
        )

    return data
