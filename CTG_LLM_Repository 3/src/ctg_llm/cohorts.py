"""Cohort selection from authorised, image-eligible study tables."""
import numpy as np
import pandas as pd
from .categories import GUIDELINES, OUTCOME, BENCHMARK


def numeric_column(data, column, allowed=None):
    if column not in data:
        raise ValueError(f"Required input column is absent: {column}")
    original = data[column].replace(r"^\s*$", np.nan, regex=True)
    numeric = pd.to_numeric(original, errors="coerce")
    if (original.notna() & numeric.isna()).any():
        raise ValueError(f"Non-numeric value in {column}")
    if (~np.isfinite(numeric.dropna())).any():
        raise ValueError(f"Non-finite value in {column}")
    if allowed is not None and not numeric.dropna().isin(allowed).all():
        raise ValueError(f"Unexpected code in {column}")
    return numeric


def prepare(data):
    data = data.copy()
    if "identifier" in data and data["identifier"].dropna().duplicated().any():
        raise ValueError("Duplicate study identifiers")
    data[OUTCOME] = numeric_column(data, OUTCOME, (0, 1))
    for spec in GUIDELINES.values():
        col = spec["column"]
        data[col] = numeric_column(data, col, spec["codes"])
        data[col + "_tier3"] = data[col].map(spec["tiers"])
    if BENCHMARK in data:
        data[BENCHMARK] = numeric_column(data, BENCHMARK, (0, 1))
    return data


def select(data, cohort="full"):
    """Apply the documented selection rules; return selected rows and counts."""
    choices = ("full", "restricted", "duration_full", "duration_restricted", "component")
    if cohort not in choices:
        raise ValueError("Unknown cohort")
    data = prepare(data)
    flow = []
    def record(stage, mask):
        flow.append({"Stage": stage, "N": int(mask.sum()),
                     "Events": int(data.loc[mask, OUTCOME].eq(1).sum())})
    mask = pd.Series(True, index=data.index)
    record("Rows supplied after image eligibility review", mask)
    columns = [spec["column"] for spec in GUIDELINES.values()]
    mask &= data[OUTCOME].isin((0, 1)) & data[columns].notna().all(axis=1)
    record("Binary outcome and all five categories available", mask)
    if "restricted" in cohort:
        intervention = numeric_column(data, "Intervened", (0, 1))
        sentinel = numeric_column(data, "Sentinel_SAFC")
        mask &= intervention.isin((0, 1))
        record("Binary intervention status available", mask)
        mask &= sentinel.ne(1)
        record("After sentinel-event exclusions", mask)
        mask &= data[OUTCOME].eq(1) | intervention.eq(0)
        record("After intervention exclusions in non-events", mask)
    if cohort.startswith("duration"):
        flag = numeric_column(data, "more_than_thirty", (0, 1))
        mask &= flag.eq(1)
        record("At least 30 minutes of interpretable CTG", mask)
    if cohort == "component":
        flag = numeric_column(data, "Asphyxia_no_acidemia", (0, 1))
        ph = numeric_column(data, "pH")
        be = numeric_column(data, "baseexcess")
        cases = mask & data[OUTCOME].eq(1) & flag.eq(1)
        if (cases & (ph.isna() | ph.lt(7.00) | be.le(-12))).any():
            raise ValueError("Selected cases do not match the study gas definition")
        mask &= data[OUTCOME].eq(0) | cases
        record("Non-biochemical cases and all non-event controls", mask)
    selected = data.loc[mask].copy()
    if set(selected[OUTCOME].unique()) != {0, 1}:
        raise ValueError("Both outcome classes are required")
    selected[OUTCOME] = selected[OUTCOME].astype(int)
    return selected, pd.DataFrame(flow)
