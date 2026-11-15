"""Ordinal analysis kernels adapted from the study GPT-5.4 analysis scripts."""
import numpy as np
from scipy.special import expit
from scipy.stats import norm, rankdata

BOOTSTRAP_REPS = 10_000

def auc_midrank(y, score):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    n_event = int(np.sum(y == 1))
    n_nonevent = int(np.sum(y == 0))
    ranks = rankdata(score, method="average")
    return float(
        (ranks[y == 1].sum() - n_event * (n_event + 1) / 2)
        / (n_event * n_nonevent)
    )


def bootstrap_auc_ci(y, score, seed, reps=BOOTSTRAP_REPS):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    event_indices = np.flatnonzero(y == 1)
    nonevent_indices = np.flatnonzero(y == 0)
    rng = np.random.default_rng(seed)
    values = np.empty(reps)
    for replicate in range(reps):
        indices = np.concatenate(
            [
                rng.choice(event_indices, event_indices.size, replace=True),
                rng.choice(nonevent_indices, nonevent_indices.size, replace=True),
            ]
        )
        values[replicate] = auc_midrank(y[indices], score[indices])
    return tuple(np.quantile(values, [0.025, 0.975]))


def cochran_armitage_test(y, score):
    y = np.asarray(y, dtype=int)
    score = np.asarray(score, dtype=float)
    n = len(y)
    n_event = y.sum()
    n_nonevent = n - n_event
    mean_score = score.mean()
    numerator = np.sum(score * y) - n_event * mean_score
    denominator = np.sqrt(
        n_event
        * n_nonevent
        * np.sum((score - mean_score) ** 2)
        / (n * (n - 1))
    )
    if denominator == 0:
        return float("nan"), float("nan")
    z_statistic = numerator / denominator
    p_value = 2 * norm.sf(abs(z_statistic))
    return float(z_statistic), float(p_value)


def holm_adjust(p_values):
    p_values = np.asarray(p_values, dtype=float)
    order = np.argsort(np.where(np.isfinite(p_values), p_values, np.inf))
    adjusted = np.full_like(p_values, np.nan)
    running_maximum = 0.0
    m = len(p_values)
    for rank, index in enumerate(order):
        if not np.isfinite(p_values[index]):
            continue
        running_maximum = max(
            running_maximum,
            (m - rank) * p_values[index],
        )
        adjusted[index] = min(1.0, running_maximum)
    return adjusted


def logistic_or_per_category(y, score):
    # This regression estimates an association. Its fitted probabilities are NOT
    # used to calculate the category-alone AUROC or to pick category thresholds.
    y, score = np.asarray(y, float), np.asarray(score, float)
    failure = {"OR": np.nan, "OR_CI_lower": np.nan, "OR_CI_upper": np.nan,
               "OR_P": np.nan, "OR_status": "Not estimable: separation, constant score, or singular information"}
    if np.unique(score).size < 2:
        return failure
    x = np.column_stack([np.ones(len(score)), score])
    beta = np.zeros(2)
    converged = False
    try:
        for _ in range(100):
            p = expit(x @ beta)
            w = np.clip(p * (1 - p), 1e-12, None)
            step = np.linalg.solve(x.T @ (x * w[:, None]), x.T @ (y - p))
            beta += step
            if not np.isfinite(beta).all() or np.max(np.abs(beta)) > 100:
                return failure
            if np.max(np.abs(step)) < 1e-12:
                converged = True
                break
        if not converged:
            return failure
        p = expit(x @ beta)
        covariance = np.linalg.inv(x.T @ (x * (p * (1 - p))[:, None]))
        se = float(np.sqrt(covariance[1, 1]))
        estimate = float(beta[1])
        if not np.isfinite(se) or se <= 0:
            return failure
        z = norm.ppf(0.975)
        return {"OR": float(np.exp(estimate)), "OR_CI_lower": float(np.exp(estimate - z * se)),
                "OR_CI_upper": float(np.exp(estimate + z * se)),
                "OR_P": float(2 * norm.sf(abs(estimate / se))),
                "OR_status": "Maximum likelihood; Wald 95% CI"}
    except (np.linalg.LinAlgError, FloatingPointError):
        return failure


def wilson_ci(successes, total, alpha=0.05):
    if total == 0:
        return np.nan, np.nan
    z = norm.ppf(1 - alpha / 2)
    proportion = successes / total
    denominator = 1 + z**2 / total
    centre = (proportion + z**2 / (2 * total)) / denominator
    half_width = (
        z
        * np.sqrt(
            proportion * (1 - proportion) / total
            + z**2 / (4 * total**2)
        )
        / denominator
    )
    return centre - half_width, centre + half_width


def binary_performance(y, prediction):
    y = np.asarray(y, dtype=int)
    prediction = np.asarray(prediction, dtype=int)
    tp = int(np.sum((prediction == 1) & (y == 1)))
    fn = int(np.sum((prediction == 0) & (y == 1)))
    fp = int(np.sum((prediction == 1) & (y == 0)))
    tn = int(np.sum((prediction == 0) & (y == 0)))
    sensitivity = tp / (tp + fn)
    specificity = tn / (tn + fp)
    sensitivity_low, sensitivity_high = wilson_ci(tp, tp + fn)
    specificity_low, specificity_high = wilson_ci(tn, tn + fp)
    return {
        "TP": tp,
        "FN": fn,
        "FP": fp,
        "TN": tn,
        "Sensitivity": sensitivity,
        "Sensitivity_CI_lower": sensitivity_low,
        "Sensitivity_CI_upper": sensitivity_high,
        "Specificity": specificity,
        "Specificity_CI_lower": specificity_low,
        "Specificity_CI_upper": specificity_high,
        "FPR": 1 - specificity,
    }
