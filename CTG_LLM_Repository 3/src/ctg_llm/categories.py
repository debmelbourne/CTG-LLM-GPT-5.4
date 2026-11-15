"""Original analysis encodings and the Supplementary Table S1 mappings."""
from numbers import Integral

GUIDELINES = {
    "RANZCOG": {"column": "ranzcog_label", "codes": (1, 2, 3, 4),
                "tiers": {1: 1, 2: 2, 3: 2, 4: 3}},
    "NICHD": {"column": "nichd_label", "codes": (0, 1, 2),
              "tiers": {0: 1, 1: 2, 2: 3}},
    "NICE/RCOG": {"column": "rcog_label", "codes": (1, 2, 3),
                  "tiers": {1: 1, 2: 2, 3: 3}},
    "Parer-Ikeda": {"column": "parer_label", "codes": (1, 2, 3, 4, 5),
                    "tiers": {1: 1, 2: 1, 3: 2, 4: 3, 5: 3}},
    "FIGO": {"column": "figo_label", "codes": (1, 2, 3),
             "tiers": {1: 1, 2: 2, 3: 3}},
}

NICHD_CLINICAL_TO_RAW = {"I": 0, "II": 1, "III": 2}
OUTCOME = "asphyxia_pick"
BENCHMARK = "Main Operative Delivery NOTFORDISTRESS_0 FORDISTRESS_1"
SEED = 20260918
TARGET_SPECIFICITIES = (0.95, 0.90, 0.85, 0.80)


def common_tier(guideline, raw_category):
    """Derive a separate tier without replacing the original category."""
    if guideline not in GUIDELINES:
        raise ValueError("Unknown guideline")
    if isinstance(raw_category, bool) or not isinstance(raw_category, Integral):
        raise ValueError("The raw category must be an integer")
    try:
        return GUIDELINES[guideline]["tiers"][int(raw_category)]
    except KeyError as exc:
        raise ValueError("Category outside the guideline's raw encoding") from exc
