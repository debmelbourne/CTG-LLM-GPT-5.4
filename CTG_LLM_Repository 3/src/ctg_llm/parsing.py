"""Deterministic category parsing and separate common-tier derivation."""
import json
from dataclasses import dataclass
from .categories import GUIDELINES, common_tier

FEATURES = ("baseline", "variability", "accelerations", "decelerations",
            "contractions", "duration_limitations")
PARSER_VERSION = "1.0.0"


@dataclass(frozen=True)
class ParsedResponse:
    guideline: str
    raw_category: int | None
    common_tier: int | None
    status: str
    features: dict | None = None


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate JSON field")
        value[key] = item
    return value


def _invalid_constant(value):
    raise ValueError("Non-finite JSON value")


def decode_response(response):
    """Decode JSON without accepting duplicate keys or non-finite numbers."""
    return (json.loads(response, object_pairs_hook=_unique_object,
                       parse_constant=_invalid_constant)
            if isinstance(response, str) else response)


def parse_response(response, guideline):
    """Return missing category fields for invalid or missing responses."""
    if guideline not in GUIDELINES:
        raise ValueError("Unknown guideline")
    empty = lambda status: ParsedResponse(guideline, None, None, status)
    if response is None or (isinstance(response, str) and not response.strip()):
        return empty("missing")
    try:
        value = decode_response(response)
        if not isinstance(value, dict):
            return empty("invalid_schema")
        required = {"guideline", "raw_category", *FEATURES}
        if set(value) != required or value["guideline"] != guideline:
            return empty("invalid_schema")
        category = value["raw_category"]
        if any(value[k] is not None and not isinstance(value[k], str) for k in FEATURES):
            return empty("invalid_schema")
        features = {k: value[k] for k in FEATURES}
        if category is None:
            return ParsedResponse(guideline, None, None, "missing_category", features)
        if type(category) not in (int, float) or category not in GUIDELINES[guideline]["codes"]:
            return empty("invalid_category")
        category = int(category)
        return ParsedResponse(guideline, category, common_tier(guideline, category),
                              "parsed", features)
    except (ValueError, TypeError):
        return empty("invalid_json")


def parse_quality(response):
    """Validate technical observations without making an eligibility decision."""
    try:
        value = decode_response(response)
        booleans = ("fhr_visible", "uterine_activity_visible")
        strings = ("duration_limitations", "quality_limitations")
        if not isinstance(value, dict) or set(value) != {*booleans, *strings}:
            return None, "invalid_schema"
        if any(value[k] is not None and type(value[k]) is not bool for k in booleans):
            return None, "invalid_schema"
        if any(value[k] is not None and not isinstance(value[k], str) for k in strings):
            return None, "invalid_schema"
        return value, "parsed"
    except (ValueError, TypeError):
        return None, "invalid_json"
