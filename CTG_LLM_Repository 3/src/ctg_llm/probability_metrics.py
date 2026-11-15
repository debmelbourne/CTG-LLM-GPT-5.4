"""Evaluation of held-out and external probability predictions.

Calibration regressions describe predictions without changing them. The
resampling definitions retain the distinction used in the study scripts.
"""
import numpy as np
import statsmodels.api as sm
from sklearn.metrics import brier_score_loss, roc_auc_score, roc_curve

SEED = 42
BOOTSTRAP_REPS = 2000
CALIBRATION_EPSILON = 1e-6


def bootstrap_auc_ci(y_true, probability, reps=BOOTSTRAP_REPS, seed=SEED):
    y_true = np.asarray(y_true, dtype=int)
    probability = np.asarray(probability, dtype=float)
    positive_indices = np.flatnonzero(y_true == 1)
    negative_indices = np.flatnonzero(y_true == 0)
    rng = np.random.default_rng(seed)
    estimates = []

    for _ in range(reps):
        sampled_positive = rng.choice(
            positive_indices, size=len(positive_indices), replace=True
        )
        sampled_negative = rng.choice(
            negative_indices, size=len(negative_indices), replace=True
        )
        sampled = np.concatenate([sampled_positive, sampled_negative])
        estimates.append(roc_auc_score(y_true[sampled], probability[sampled]))

    lower, upper = np.quantile(estimates, [0.025, 0.975])
    return float(lower), float(upper)

def sensitivity_at_fpr(y_true, probability, maximum_fpr):
    fpr, tpr, _ = roc_curve(y_true, probability)
    eligible = tpr[fpr <= maximum_fpr]
    return float(eligible.max()) if len(eligible) else 0.0

def calibration_intercept_slope(y_true, probability):
    probability = np.clip(np.asarray(probability, dtype=float), 1e-6, 1 - 1e-6)
    logit_probability = np.log(probability / (1.0 - probability))
    design = sm.add_constant(logit_probability, has_constant="add")
    try:
        model = sm.GLM(
            np.asarray(y_true, dtype=int),
            design,
            family=sm.families.Binomial(),
        ).fit()
        return float(model.params[0]), float(model.params[1])
    except Exception:
        return np.nan, np.nan

def stratified_bootstrap_indices(y_true, rng):
    y_true = np.asarray(y_true, dtype=int)
    positive = np.flatnonzero(y_true == 1)
    negative = np.flatnonzero(y_true == 0)
    sampled_positive = rng.choice(
        positive,
        size=len(positive),
        replace=True,
    )
    sampled_negative = rng.choice(
        negative,
        size=len(negative),
        replace=True,
    )
    return np.concatenate([sampled_positive, sampled_negative])

def bootstrap_auc_and_brier_ci(
    y_true,
    probability,
    reps=BOOTSTRAP_REPS,
    seed=SEED,
):
    y_true = np.asarray(y_true, dtype=int)
    probability = np.asarray(probability, dtype=float)
    auc_rng = np.random.default_rng(seed)
    brier_rng = np.random.default_rng(seed + 1)
    auc_estimates = []
    brier_estimates = []

    for _ in range(reps):
        auc_sampled = stratified_bootstrap_indices(
            y_true,
            auc_rng,
        )
        auc_estimates.append(
            roc_auc_score(
                y_true[auc_sampled],
                probability[auc_sampled],
            )
        )
        brier_sampled = brier_rng.integers(
            0,
            len(y_true),
            size=len(y_true),
        )
        brier_estimates.append(
            brier_score_loss(
                y_true[brier_sampled],
                probability[brier_sampled],
            )
        )

    return {
        "auroc_ci_lower": float(
            np.quantile(auc_estimates, 0.025)
        ),
        "auroc_ci_upper": float(
            np.quantile(auc_estimates, 0.975)
        ),
        "brier_ci_lower": float(
            np.quantile(brier_estimates, 0.025)
        ),
        "brier_ci_upper": float(
            np.quantile(brier_estimates, 0.975)
        ),
    }

def paired_bootstrap_auc_difference_ci(
    y_true,
    strategy_probability,
    clinical_probability,
    reps=BOOTSTRAP_REPS,
    seed=SEED,
):
    y_true = np.asarray(y_true, dtype=int)
    strategy_probability = np.asarray(
        strategy_probability,
        dtype=float,
    )
    clinical_probability = np.asarray(
        clinical_probability,
        dtype=float,
    )
    rng = np.random.default_rng(seed)
    differences = []

    for _ in range(reps):
        sampled = stratified_bootstrap_indices(y_true, rng)
        strategy_auc = roc_auc_score(
            y_true[sampled],
            strategy_probability[sampled],
        )
        clinical_auc = roc_auc_score(
            y_true[sampled],
            clinical_probability[sampled],
        )
        differences.append(strategy_auc - clinical_auc)

    return (
        float(np.quantile(differences, 0.025)),
        float(np.quantile(differences, 0.975)),
    )

def sensitivity_at_maximum_fpr(
    y_true,
    probability,
    maximum_fpr,
):
    fpr, tpr, _ = roc_curve(y_true, probability)
    eligible = tpr[fpr <= maximum_fpr]
    return float(eligible.max()) if len(eligible) else 0.0

def calibration_statistics(y_true, probability):
    probability = np.clip(
        np.asarray(probability, dtype=float),
        CALIBRATION_EPSILON,
        1.0 - CALIBRATION_EPSILON,
    )
    logit_probability = np.log(
        probability / (1.0 - probability)
    )
    design = sm.add_constant(
        logit_probability,
        has_constant="add",
    )

    try:
        model = sm.GLM(
            np.asarray(y_true, dtype=int),
            design,
            family=sm.families.Binomial(),
        ).fit()
        confidence_interval = np.asarray(model.conf_int(alpha=0.05))
        return {
            "calibration_intercept": float(model.params[0]),
            "calibration_intercept_ci_lower": float(
                confidence_interval[0, 0]
            ),
            "calibration_intercept_ci_upper": float(
                confidence_interval[0, 1]
            ),
            "calibration_slope": float(model.params[1]),
            "calibration_slope_ci_lower": float(
                confidence_interval[1, 0]
            ),
            "calibration_slope_ci_upper": float(
                confidence_interval[1, 1]
            ),
        }
    except Exception:
        return {
            "calibration_intercept": np.nan,
            "calibration_intercept_ci_lower": np.nan,
            "calibration_intercept_ci_upper": np.nan,
            "calibration_slope": np.nan,
            "calibration_slope_ci_lower": np.nan,
            "calibration_slope_ci_upper": np.nan,
        }


def validate_predictions(y_true, probability):
    y = np.asarray(y_true)
    p = np.asarray(probability, dtype=float)
    if y.ndim != 1 or p.ndim != 1 or len(y) != len(p):
        raise ValueError("Outcomes and probabilities require matching one-dimensional arrays")
    if set(np.unique(y)) != {0, 1}:
        raise ValueError("Both binary outcome classes are required")
    if not np.isfinite(p).all() or ((p < 0) | (p > 1)).any():
        raise ValueError("Probabilities must be finite values between zero and one")
    return y.astype(int), p


def evaluate_probabilities(y_true, probability, *, stage="external", reference=None,
                           seed=SEED, reference_seed=None, reps=BOOTSTRAP_REPS):
    """Summarise existing predictions; no predictor or probability model is fitted."""
    y, p = validate_predictions(y_true, probability)
    if stage not in {"heldout", "external"}:
        raise ValueError("stage must be heldout or external")
    if not isinstance(reps, int) or isinstance(reps, bool) or reps < 1:
        raise ValueError("reps must be a positive integer")
    ref = None
    if reference is not None:
        if stage != "external":
            raise ValueError("Paired reference comparison is defined for external evaluation")
        _, ref = validate_predictions(y, reference)
    result = {"n": int(len(y)), "events": int(y.sum()), "event_rate": float(y.mean()),
              "auroc": float(roc_auc_score(y, p)),
              "brier_score": float(brier_score_loss(y, p)),
              "sensitivity_at_90_specificity": sensitivity_at_fpr(y, p, 0.10),
              "sensitivity_at_85_specificity": sensitivity_at_fpr(y, p, 0.15)}
    if stage == "heldout":
        low, high = bootstrap_auc_ci(y, p, reps=reps, seed=seed)
        intercept, slope = calibration_intercept_slope(y, p)
        result.update(auroc_ci_lower=low, auroc_ci_upper=high,
                      calibration_intercept=intercept, calibration_slope=slope)
    else:
        result.update(bootstrap_auc_and_brier_ci(y, p, reps=reps, seed=seed))
        result.update(calibration_statistics(y, p))
    if ref is not None:
        low, high = paired_bootstrap_auc_difference_ci(
            y, p, ref, reps=reps, seed=seed if reference_seed is None else reference_seed)
        result.update(delta_auroc_vs_reference=float(roc_auc_score(y, p)-roc_auc_score(y, ref)),
                      delta_auroc_ci_lower=low, delta_auroc_ci_upper=high)
    return result
