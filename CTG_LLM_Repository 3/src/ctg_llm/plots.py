"""Empirical category ROC and association figures."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00"]


def figures(roc, associations, directory, benchmark=None):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    datasets = list(associations.Dataset.unique())
    fig, axes = plt.subplots(1, len(datasets), figsize=(6 * len(datasets), 5.6), squeeze=False)
    for ax, dataset in zip(axes[0], datasets):
        subset = roc.loc[roc.Dataset.eq(dataset)]
        for color, (name, group) in zip(COLORS, subset.groupby("Guideline", sort=False)):
            estimate = associations.loc[associations.Dataset.eq(dataset) & associations.Guideline.eq(name), "AUROC"].iloc[0]
            ax.plot(group.FPR, group.Sensitivity, "o-", color=color, markersize=4,
                    label=f"{name}: {estimate:.3f}")
        ax.plot([0, 1], [0, 1], "--", color="0.65", linewidth=1)
        if dataset == "Australian dataset" and benchmark is not None and not benchmark.empty:
            row = benchmark.iloc[0]
            ax.scatter(1-row.Specificity, row.Sensitivity, marker="D", color="black",
                       label="Clinician-management benchmark", zorder=5)
        ax.set(xlim=(0, 1), ylim=(0, 1.02), xlabel="1 - specificity", ylabel="Sensitivity", title=dataset)
        ax.set_aspect("equal", adjustable="box")
        ax.legend(loc="lower right", fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(directory / "raw_category_roc.png", dpi=300)
    fig.savefig(directory / "raw_category_roc.pdf")
    plt.close(fig)
    for estimate, title, null in (("AUROC", "Category-alone AUROC", .5), ("OR", "Odds ratio per category increase", 1)):
        fig, ax = plt.subplots(figsize=(8, max(4.5, .45 * len(associations))))
        for i, row in associations.reset_index(drop=True).iterrows():
            value, low, high = row[estimate], row[estimate+"_CI_lower"], row[estimate+"_CI_upper"]
            if np.isfinite([value, low, high]).all():
                ax.errorbar(value, i, xerr=[[value-low], [high-value]], fmt="o", color=COLORS[i % 5], capsize=3)
        ax.set_yticks(range(len(associations)), [f"{r.Dataset} — {r.Guideline}" for r in associations.itertuples()])
        ax.invert_yaxis()
        ax.axvline(null, color="0.65", linestyle="--")
        ax.set_xlabel(title)
        if estimate == "OR":
            ax.set_xscale("log")
        fig.tight_layout()
        fig.savefig(directory / (estimate.lower()+"_forest.png"), dpi=300)
        fig.savefig(directory / (estimate.lower()+"_forest.pdf"))
        plt.close(fig)
