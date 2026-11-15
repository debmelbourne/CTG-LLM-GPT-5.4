# Analysis contract

## Inputs

The record-level interface accepts CSV or the first worksheet of an XLSX file. Inputs represent records already adjudicated as image-eligible. This package does not infer image eligibility from GPT quality ratings. Missing outcome/category fields are excluded from the common complete-category analysis and counted in the output flow. Unexpected codes or non-numeric values produce an error. Source row order is preserved.

| Field | Meaning and use |
| --- | --- |
| `identifier` | Optional de-identified study ID; duplicate non-missing IDs are rejected |
| `asphyxia_pick` | Existing adjudicated composite outcome, 0 or 1; never recomputed from a GPT response |
| `ranzcog_label` | Raw code 1–4 |
| `nichd_label` | Raw code 0–2 |
| `rcog_label` | Raw NICE code 1–3 |
| `parer_label` | Raw code 1–5 |
| `figo_label` | Raw code 1–3 |
| `Main Operative Delivery NOTFORDISTRESS_0 FORDISTRESS_1` | Optional Australian benchmark: code 1 is positive; 0 or blank is not positive, as defined in the manuscript |
| `Sentinel_SAFC` | Restricted analyses: only code 1 denotes exclusion; other numeric codes are not reclassified |
| `Intervened` | Broader intervention indicator, distinct from the management benchmark; restricted analyses require 0 or 1 and exclude non-events with code 1 |
| `more_than_thirty` | Recorded flag for at least 30 minutes of interpretable CTG; code 1 is retained |
| `Asphyxia_no_acidemia` | Existing case-subgroup flag; component analysis retains flagged composite cases and all non-event controls |
| `pH`, `baseexcess` | Component-analysis checks: selected cases require recorded pH ≥7.00 and no recorded base excess ≤−12; missing base excess is retained |

The component-analysis flag is retained. Selected cases require recorded pH ≥7.00 and no documented base excess ≤−12 mmol/L, consistent with the study definition; missing base excess is allowed.

`ctu_asphyxia` expresses the external composite as 5-minute Apgar <5, arterial pH <7.00 or base excess ≤−12 mmol/L. A positive recorded component is sufficient. When no component is positive but at least one is unavailable, the generic mapper returns missing for adjudication; it does not assume an unaffected outcome. Published analyses use the existing adjudicated `asphyxia_pick` field.

## Calculations

Raw categories are used directly for AUROC, with midranks for ties. The univariable logistic regression estimates the odds ratio per original category increment; its fitted probabilities are not used for category AUROC. The Cochran–Armitage test uses consecutive category scores. Holm adjustment is applied across the five guideline tests separately within each cohort and scale. Category proportions, sensitivity and specificity use Wilson intervals. AUROC intervals use 10,000 outcome-stratified percentile bootstrap replicates by default.

Every empirical raw-category ROC point is retained and adjacent points are joined linearly. Australian thresholds maximise sensitivity subject to specificity of at least 95%, 90%, 85% or 80%. Ties follow the study scripts' sensitivity-then-FPR ordering. The no-positive rule is included. Selected numeric thresholds are applied unchanged to CTU-UHB. Duration-subset thresholds are selected within the respective Australian subset. Category thresholds and harmonised tiers remain separate outputs.

Restricted analyses do not repeat the clinician benchmark or discordance analysis. For unrestricted analyses, blank benchmark codes follow the manuscript's no-recorded-distress-intervention convention and their number is reported. Discordance is descriptive and does not estimate avoidable interventions or preventable asphyxia.

Bootstrap resampling uses the fixed starting seed 20260918. Fixed numbers are added to this seed to select repeatable random-number sequences for the different analyses; for example, adding 100 gives 20261018. These additions, also called seed offsets, control the resampling used for confidence intervals. They do not modify input signals, category values or point estimates. Guideline order is RANZCOG, NICHD, NICE/RCOG, Parer–Ikeda, FIGO. Raw-category seed additions are 0 for Australia, 100 for CTU-UHB, 1000 for the duration subset and 100 for the outcome-component comparison. Common-tier analyses add 200; benchmark seed additions are 500, 1500 and 600 respectively. The original full and restricted analyses use the same seed schedule. Exact bootstrap samples also depend on original record order.

## Command interface

`ctg-llm analyse` accepts `--australian`, optional `--ctu`, `--cohort` and `--output`. The output directory is empty at the start of a run. `--bootstrap-reps` defaults to 10000; `--no-figures` suppresses figure exports. Paths are runtime arguments for authorised local files.

| Analysis | Cohort option and external scope |
| --- | --- |
| Full category analysis | `--cohort full`; optional CTU threshold transport |
| Restricted Australian analysis | `--cohort restricted`; optional independent CTU evaluation and threshold transport |
| At least 30 minutes | `--cohort duration_full`; Australian subset |
| At least 30 minutes after restrictions | `--cohort duration_restricted`; Australian subset |
| Outcome-component comparison | `--cohort component`; Australian subset |
| Structured-response parsing | `ctg-llm parse` with `--input`, `--output` and optional `--wide-output` |

Executable secondary predictor preparation, partitioning and probability evaluation are described in [Secondary modelling](secondary_model.md).

The parser accepts the final audit records produced by `ctg-llm-infer`, or one JSON object per line with `study_id`, `guideline` and `response`. The response is either a JSON object or its serialised JSON string. The applicable response contract is in `src/ctg_llm/resources/schemas/`. A study ID/guideline pair occurs at most once. Quality records are omitted from category output. The optional `--wide-output` writes the five raw label columns by identifier for a separate authorised join; it contains no outcome or clinical fields. Parsed output keeps `raw_category`, `common_tier` and status in separate columns; it is not joined to clinical tables automatically.

## Outputs

CSV outputs contain cohort-flow counts, category counts, association estimates, empirical ROC points, attainable and selected thresholds, transported thresholds, and applicable benchmark/discordance summaries. Figures are exported as vector PDF and 300-dpi PNG. The run manifest records input checksums, software versions and analysis settings without absolute data paths.
