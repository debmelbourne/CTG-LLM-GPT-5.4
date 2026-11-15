# Secondary modelling

The secondary analysis compares recorded variables alone with five strategies that each add one common-tier GPT category. Full and restricted Australian cohorts are modelled separately. The public implementation exposes predictor preparation, partitioning and evaluation of existing predictions; model fitting and combination are described below.

## Predictor preparation

`src/ctg_llm/secondary.py` contains `engineer_features`, `engineer_external_features`, `make_model_frame` and `make_four_way_split`, adapted from the two secondary source scripts.

| Predictor type | Fields |
| --- | --- |
| Continuous | `Gestation`, `Maternal_age`, `Duration_of_labour_1`, `Duration_of_labour_2`, `Duration_stage_total`, `ECG_Trace_duration`, `US_Trace_duration` |
| Categorical | `Meconeum`, `Labour_onset_svsi`, `Fetal_presention`, `Maternal_position`, `Fetal_position`, `Regional_anaesthetic`, `OBS_CODE`, `BMI_category`, `Parity_binary` |
| Strategy-specific additional predictor | One of `ranzcog_enc`, `nichd_enc`, `parer_enc`, `figo_enc`, `rcog_enc`, using Supplementary Table S1 mappings |

BMI categories are <18.5, 18.5–<25, 25–<30 and ≥30 kg/m², with an explicit missing category. Parity distinguishes zero from nonzero with an explicit missing category. Labour-onset codes 0/1 map to spontaneous/induced and presentation codes 0/1 to cephalic/breech; other values form an unknown category. The original field spellings are retained for compatibility with prepared study inputs.

ECG acquisition duration sums `FHR1ModeDECGdur` and `FHR2ModeDECGdur`; ultrasound acquisition duration sums `FHR1ModeUSdur` and `FHR2ModeUSdur`. An entirely missing pair remains missing. External inputs can instead contain the two already derived duration fields. These acquisition durations are distinct from the interpretable-CTG flag used in duration sensitivity analyses.

The prepared CTU study inputs use `Maternal_BMI = 25` kg/m². The feature functions categorise the supplied BMI field. Outcomes, management indicators and other guideline categories are excluded from each declared predictor set.

## Partitioning and model specification

The stratified split allocates 60% to training, 15% to stacking, 10% to calibration and 15% to held-out testing. It uses seed 42 for test allocation and seeds 43 and 44 for subsequent calibration and stacking allocation. Integer partition sizes follow sequential `train_test_split` rounding. Partitioning validates unique rows and study identifiers and checks disjointness and complete coverage.

Training-only preprocessing includes continuous imputation and applicable scaling. The three base learners are CatBoost, TabNet and logistic regression. XGBoost combines their probabilities in the stacking partition. Positive-slope logistic calibration is fitted in the calibration partition. The test partition is excluded from fitting and early stopping. The external pipeline reuses the locked preprocessing, predictor set, learners, combination and calibration. [Pseudocode](secondary_model_pseudocode.txt) describes this sequence.

## Probability evaluation

`src/ctg_llm/probability_metrics.py` evaluates existing probability predictions. It calculates AUROC, Brier score, sensitivity at attainable specificity of at least 90% and 85%, and calibration intercept and slope. Calibration regressions describe predictions without altering them.

Held-out AUROC intervals use outcome-stratified percentile bootstrap resampling. External summaries use separate random streams: outcome-stratified resampling for AUROC, ordinary resampling for Brier score, and paired outcome-stratified resampling for an AUROC difference from recorded-variables-only predictions. The default is 2,000 replicates. External calibration regressions also provide 95% intervals for the intercept and slope.

The source strategy order is recorded variables only, RANZCOG, NICHD, Parer–Ikeda, FIGO and NICE/RCOG. For strategy number j starting at 1, the AUROC/Brier starting seed is 42 + 100j and the paired AUROC-difference seed is 42 + 1000j. The Brier stream adds 1 to its starting seed. Both seeds are explicit evaluation-interface options. These probability summaries are distinct from primary category-threshold transport.

## Public interfaces

| Command | Input and output |
| --- | --- |
| `ctg-llm prepare-secondary` | Required `--australian` and `--output`; optional `--ctu`; `--cohort` is `full` or `restricted`; `--seed` defaults to 42. Outputs declared predictors, Australian partition assignments, cohort flow and a run manifest. |
| `ctg-llm evaluate-probabilities` | Required `--input`, `--probability-column` and `--output`; `--stage` is `heldout` or `external`. Inputs contain `asphyxia_pick` and the declared probability column. Optional `--reference-column` and `--reference-seed` support an external paired comparison. Outputs one metrics table and a run manifest. |

All inputs are authorised local CSV or XLSX tables. Runtime outputs are generated from those inputs; no prepared tables or predictions are distributed. Model fitting, protected integration and trained artifacts follow [Code and data availability](../CODE_AND_DATA_AVAILABILITY.md).
