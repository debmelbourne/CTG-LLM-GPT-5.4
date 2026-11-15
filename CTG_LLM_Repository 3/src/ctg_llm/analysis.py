"""Category counts, association estimates, thresholds and management discordance."""
import numpy as np
import pandas as pd
from sklearn.metrics import roc_curve
from .categories import GUIDELINES, OUTCOME, BENCHMARK, SEED, TARGET_SPECIFICITIES
from .statistics import (auc_midrank, bootstrap_auc_ci, cochran_armitage_test,
                         logistic_or_per_category, holm_adjust, wilson_ci,
                         binary_performance)


def category_counts(y, score, categories):
    rows = []
    y, score = np.asarray(y), np.asarray(score)
    for category in categories:
        selected = score == category
        n, events = int(selected.sum()), int(y[selected].sum())
        low, high = wilson_ci(events, n)
        rows.append({"Category": category, "N": n, "Events": events,
                     "Proportion": events / n if n else np.nan,
                     "Proportion_CI_lower": low, "Proportion_CI_upper": high})
    return pd.DataFrame(rows)


def association(y, score, seed, reps=10000):
    y, score = np.asarray(y, dtype=int), np.asarray(score, dtype=float)
    if len(y) != len(score) or set(np.unique(y)) != {0, 1} or not np.isfinite(score).all():
        raise ValueError("Finite scores and both binary outcome classes are required")
    z, p = cochran_armitage_test(y, score)
    low, high = bootstrap_auc_ci(y, score, seed=seed, reps=reps)
    return {"N": len(y), "Events": int(y.sum()), "Cochran_Armitage_Z": z,
            "Cochran_Armitage_P": p, **logistic_or_per_category(y, score),
            "AUROC": auc_midrank(y, score), "AUROC_CI_lower": low,
            "AUROC_CI_upper": high}


def thresholds(y, score):
    score = np.asarray(score, float)
    rows = [{"Threshold": np.inf, "Rule": "No positive classifications",
             **binary_performance(y, np.zeros(len(score), int))}]
    for threshold in sorted(np.unique(score), reverse=True):
        rows.append({"Threshold": threshold, "Rule": f">= {threshold:g}",
                     **binary_performance(y, score >= threshold)})
    return pd.DataFrame(rows)


def select_thresholds(table):
    rows = []
    for target in TARGET_SPECIFICITIES:
        eligible = table.loc[table.Specificity >= target]
        # Same sensitivity/FPR tie order as the study analysis scripts.
        chosen = eligible.sort_values(["Sensitivity", "FPR"],
                                      ascending=[False, False]).iloc[0].to_dict()
        rows.append({"Target_specificity": target, **chosen})
    return pd.DataFrame(rows)


def analyse_table(data, dataset, tier=False, seed_offset=0, reps=10000):
    rows, counts, points, curves = [], [], [], []
    y = data[OUTCOME].to_numpy(int)
    for i, (name, spec) in enumerate(GUIDELINES.items()):
        score = data[spec["column"] + ("_tier3" if tier else "")].to_numpy(float)
        meta = {"Dataset": dataset, "Guideline": name, "Scale": "tier3" if tier else "raw"}
        rows.append({**meta, **association(y, score, SEED + seed_offset + i, reps)})
        counts.append(category_counts(y, score, (1, 2, 3) if tier else spec["codes"]).assign(**meta))
        if not tier:
            points.append(thresholds(y, score).assign(**meta))
            fpr, tpr, cutoff = roc_curve(y, score, drop_intermediate=False)
            curves.append(pd.DataFrame({"FPR": fpr, "Sensitivity": tpr,
                                        "Threshold": cutoff}).assign(**meta))
    results = pd.DataFrame(rows)
    results["Cochran_Armitage_Holm_P"] = holm_adjust(results.Cochran_Armitage_P)
    return {"associations": results, "counts": pd.concat(counts, ignore_index=True),
            "thresholds": pd.concat(points, ignore_index=True) if points else pd.DataFrame(),
            "roc_points": pd.concat(curves, ignore_index=True) if curves else pd.DataFrame()}


def select_by_guideline(table):
    return pd.concat([select_thresholds(group).assign(Guideline=name)
                      for name, group in table.groupby("Guideline", sort=False)], ignore_index=True)


def transport(selected, external):
    rows = []
    y = external[OUTCOME].to_numpy(int)
    for _, row in selected.iterrows():
        score = external[GUIDELINES[row.Guideline]["column"]].to_numpy(float)
        performance = binary_performance(y, score >= row.Threshold)
        rows.append({"Guideline": row.Guideline, "Australian_target_specificity": row.Target_specificity,
                     "Threshold": row.Threshold, "Australian_sensitivity": row.Sensitivity,
                     "Australian_specificity": row.Specificity,
                     **{"CTU_" + k: v for k, v in performance.items()}})
    return pd.DataFrame(rows)


def benchmark(data, reps=10000, seed_offset=500):
    if BENCHMARK not in data:
        return pd.DataFrame(), pd.DataFrame()
    y = data[OUTCOME].to_numpy(int)
    action = data[BENCHMARK].eq(1).to_numpy(int)
    low, high = bootstrap_auc_ci(y, action, seed=SEED + seed_offset, reps=reps)
    performance = pd.DataFrame([{**binary_performance(y, action),
        "AUROC": auc_midrank(y, action), "AUROC_CI_lower": low,
        "AUROC_CI_upper": high, "Missing_benchmark_codes": int(data[BENCHMARK].isna().sum())}])
    rows = []
    for managed, outcome in ((1, 1), (1, 0), (0, 1), (0, 0)):
        mask = (action == managed) & (y == outcome)
        for name, spec in GUIDELINES.items():
            tier = data.loc[mask, spec["column"] + "_tier3"]
            n = len(tier)
            rows.append({"Benchmark_intervention": managed, "Observed_asphyxia": outcome,
                         "Guideline": name, "N": n,
                         "Low": int(tier.eq(1).sum()), "Intermediate": int(tier.eq(2).sum()),
                         "High": int(tier.eq(3).sum()),
                         "Intermediate_or_high": int(tier.ge(2).sum()),
                         "Intermediate_or_high_percent": 100 * tier.ge(2).sum() / n if n else np.nan})
    return performance, pd.DataFrame(rows)
