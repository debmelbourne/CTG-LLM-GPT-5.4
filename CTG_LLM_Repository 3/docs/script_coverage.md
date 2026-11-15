# Coverage of the source analysis scripts

The supplied archive contains six Python files: four category/sensitivity analysis scripts and two secondary-model scripts. Their SHA-256 hashes match the sources recorded in `source_manifest.json`.

| Source analysis | Elements represented in the public package | Location |
| --- | --- | --- |
| Full direct-category analysis | Original encodings, common tiers, category counts, trend tests, odds ratios, AUROC, stratified intervals, Wilson intervals, empirical ROC points, Australian thresholds, CTU threshold transport and management discordance | `categories.py`, `cohorts.py`, `statistics.py`, `analysis.py`, `plots.py`; `analyse --cohort full` |
| Restricted direct-category analysis | Common complete-category cohort; sentinel and intervention exclusions in Australia; independent CTU evaluation; no restricted-cohort clinician benchmark | `cohorts.py`, `analysis.py`; `analyse --cohort restricted` |
| Duration sensitivity analyses | At least 30 minutes of interpretable CTG, full and restricted variants, subset-specific estimates and thresholds, and the full-subset management comparison | `cohorts.py`, `analysis.py`; `analyse --cohort duration_full` and `duration_restricted` |
| Outcome-component sensitivity analysis | Existing non-biochemical case flag, gas-definition checks, all eligible non-event controls, raw-category comparisons and management benchmark | `cohorts.py`, `outcomes.py`, `analysis.py`; `analyse --cohort component` |
| Full secondary multivariable analysis | Sixteen recorded predictors, BMI/parity categories, categorical mappings, acquisition-duration derivation, common-tier predictors, stratified four-way split, held-out and external probability metrics, paired external AUROC differences | `secondary.py`, `probability_metrics.py`; `prepare-secondary --cohort full`; `evaluate-probabilities` |
| Restricted secondary multivariable analysis | The corresponding preparation, split and evaluation procedures after Australian restrictions, with separately fitted models in the study implementation | `cohorts.py`, `secondary.py`, `probability_metrics.py`; `prepare-secondary --cohort restricted`; `evaluate-probabilities` |

The two secondary source scripts share the same public preparation, partitioning and evaluation functions. Base-learner fitting, stacking, calibration fitting and locked model integration are represented by the method specification and pseudocode, consistent with the manuscript's code-availability scope.

The source analysis scripts operate on precomputed guideline categories. Azure inference, structured parsing and CTU rendering are additional public components adapted from the earlier reproducibility package and the study methods. The repository excludes notebook upload handlers, institutional paths, credentials, model artifacts and completed analysis outputs.
