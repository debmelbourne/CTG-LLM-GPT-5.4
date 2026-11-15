# Reproducibility scope

The public software consolidates calculations from six source analysis scripts. It preserves the raw category encodings, Supplementary Table S1 mappings, cohort rules, statistical definitions and resampling conventions. Source hashes and public destinations are recorded in `source_manifest.json`; [Script coverage](script_coverage.md) describes the correspondence.

The category-analysis interfaces cover the full and restricted cohorts, duration sensitivity analyses, outcome-component comparison, Australian threshold selection, CTU threshold transport and clinician-management discordance. Secondary-model resources include executable predictor preparation, four-way partitioning and probability-evaluation functions. Model fitting and combination are described in the [secondary-model specification](secondary_model.md).

The Azure interface uses a separate technical-quality request and five independent guideline-specific requests. Parsing retains original categories and derives common tiers separately. Human adjudication determines image eligibility. Public prompts are reference templates for the documented interface; retained study prompts, images and deployment records are governed study material covered by [Code and data availability](../CODE_AND_DATA_AVAILABILITY.md).

The CTU rendering command retains the earlier public renderer's numerical operations and defaults, with its import path updated for this package. FHR interpolation is confined to contiguous valid segments. TOCO processing includes limited interpolation of missing samples and rolling-mean smoothing.

Each analysis run records its inputs, checksums, software versions and settings. Inference audits retain the request interface and service configuration. The public release environment is documented separately from study execution records. No participant records, simulated datasets or published results tables are included.
