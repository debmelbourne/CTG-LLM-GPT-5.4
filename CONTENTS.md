# Repository contents

This repository provides reusable components for CTG image classification and analysis. It contains code, reference prompts, response contracts, method specifications and software checks. Study-specific data, images, responses, fitted models and published results tables follow the access arrangements in `CODE_AND_DATA_AVAILABILITY.md`.

## Repository overview and release files

| File | Purpose |
| --- | --- |
| [.gitignore](.gitignore) | Version-control exclusions for local data, results and audit directories, environment files, and Python build/cache files. |
| [CITATION.cff](CITATION.cff) | Machine-readable software citation, authors, release version and licence. |
| [CODE_AND_DATA_AVAILABILITY.md](CODE_AND_DATA_AVAILABILITY.md) | Study-data request arrangements, institutional access conditions and public software scope. |
| [CONTENTS.md](CONTENTS.md) | File-by-file descriptions of the repository contents. |
| [LICENSE](LICENSE) | BSD 3-Clause terms for reuse of the public software. |
| [MANIFEST.sha256](MANIFEST.sha256) | SHA-256 checksums for all other distributed files. |
| [README.md](README.md) | Study context, public software scope and links to the repository components. |
| [VERIFICATION.md](VERIFICATION.md) | Completed software checks, source comparisons and the scope of verification. |
| [pyproject.toml](pyproject.toml) | Package metadata, exact direct dependencies, optional dependency groups, resources and command entry points. |
| [requirements.txt](requirements.txt) | Exact direct dependencies for the core analysis package. |
| [source_manifest.json](source_manifest.json) | Hashes of the six source scripts, their public destinations and rendering-code provenance. |

## Executable rendering command

| File | Purpose |
| --- | --- |
| [scripts/render_ctu_signals.py](scripts/render_ctu_signals.py) | Executable CTU-UHB WFDB/CSV rendering command with image output and a rendering manifest. |

## Method and interface documentation

| File | Purpose |
| --- | --- |
| [docs/analysis.md](docs/analysis.md) | Analysis input fields, cohort options, category statistics, threshold transport and output definitions. |
| [docs/guidelines.md](docs/guidelines.md) | The five guideline references, relevant editions, raw category encodings and common-tier mappings. |
| [docs/inference.md](docs/inference.md) | Azure input contract, deployment settings, independent requests, response handling and audit structure. |
| [docs/rendering.md](docs/rendering.md) | Signal preprocessing, FHR and TOCO missing-signal rules, display settings and rendering traceability. |
| [docs/reproducibility.md](docs/reproducibility.md) | Relationship between the public components, source analyses and controlled study records. |
| [docs/script_coverage.md](docs/script_coverage.md) | Source-by-source mapping of all six analysis scripts to executable public functions or method specifications. |
| [docs/secondary_model.md](docs/secondary_model.md) | Secondary predictor definitions, partitioning, model-combination method, probability metrics and public interfaces. |
| [docs/secondary_model_pseudocode.txt](docs/secondary_model_pseudocode.txt) | Algorithmic sequence for training, stacking, calibration, held-out evaluation and locked external application. |

## Software environment

| File | Purpose |
| --- | --- |
| [environment/README.md](environment/README.md) | Concrete software versions, dependency groups, release-date cutoff and verification-environment definitions. |
| [environment/requirements-evaluation.txt](environment/requirements-evaluation.txt) | Pinned statsmodels and patsy dependencies for probability-evaluation calibration regressions. |
| [environment/requirements-inference.txt](environment/requirements-inference.txt) | Pinned OpenAI SDK, Azure authentication/storage and JSON-schema dependencies. |
| [environment/requirements-rendering.txt](environment/requirements-rendering.txt) | Pinned WFDB dependency for CTU signal input. |
| [environment/requirements-verified.txt](environment/requirements-verified.txt) | Complete pinned dependency environment used for public verification. |
| [environment/software_versions.json](environment/software_versions.json) | Selected software releases, publication dates, official sources and public/specification scope. |
| [environment/verification_environment.json](environment/verification_environment.json) | Machine-readable interpreter and package versions loaded during verification. |

## Python modules

| File | Purpose |
| --- | --- |
| [src/ctg_llm/__init__.py](src/ctg_llm/__init__.py) | Public package release identifier. |
| [src/ctg_llm/analysis.py](src/ctg_llm/analysis.py) | Category summaries, association estimates, empirical operating points, Australian thresholds, CTU transport and management discordance. |
| [src/ctg_llm/categories.py](src/ctg_llm/categories.py) | Original guideline encodings, common three-tier mappings, outcome/benchmark names and primary seed constants. |
| [src/ctg_llm/cli.py](src/ctg_llm/cli.py) | Analysis, response-parsing, secondary-preparation and probability-evaluation command interfaces and run manifests. |
| [src/ctg_llm/cohorts.py](src/ctg_llm/cohorts.py) | Complete-category eligibility, restricted-cohort rules, duration subsets and outcome-component selection. |
| [src/ctg_llm/inference.py](src/ctg_llm/inference.py) | Azure OpenAI requests, Entra authentication, image handling, retries, audit logging and resumable execution. |
| [src/ctg_llm/outcomes.py](src/ctg_llm/outcomes.py) | Generic CTU composite mapping with explicit handling of unavailable outcome components. |
| [src/ctg_llm/parsing.py](src/ctg_llm/parsing.py) | Strict structured-response parsing with separate original categories, common tiers and missing/invalid statuses. |
| [src/ctg_llm/plots.py](src/ctg_llm/plots.py) | Generic empirical ROC and odds-ratio figures generated from analysis outputs. |
| [src/ctg_llm/probability_metrics.py](src/ctg_llm/probability_metrics.py) | Evaluation of existing predictions: AUROC, Brier score, attainable sensitivities, calibration statistics and paired AUROC differences. |
| [src/ctg_llm/rendering.py](src/ctg_llm/rendering.py) | Retained signal readers, fixed preprocessing, valid FHR segment handling, TOCO processing and image plotting. |
| [src/ctg_llm/secondary.py](src/ctg_llm/secondary.py) | Executable recorded-variable transformations, common-tier predictors, four-way stratified partitioning and predictor frames. |
| [src/ctg_llm/statistics.py](src/ctg_llm/statistics.py) | Midrank AUROC, stratified intervals, trend tests, per-category odds ratios, Holm adjustment and Wilson intervals. |

## Prompts and response contracts

| File | Purpose |
| --- | --- |
| [src/ctg_llm/resources/prompts/figo.txt](src/ctg_llm/resources/prompts/figo.txt) | FIGO three-category interpretation reference prompt. |
| [src/ctg_llm/resources/prompts/nice_ng229.txt](src/ctg_llm/resources/prompts/nice_ng229.txt) | NICE NG229 interpretation reference prompt. |
| [src/ctg_llm/resources/prompts/nichd.txt](src/ctg_llm/resources/prompts/nichd.txt) | NICHD three-category interpretation reference prompt. |
| [src/ctg_llm/resources/prompts/parer_ikeda.txt](src/ctg_llm/resources/prompts/parer_ikeda.txt) | Parer–Ikeda five-tier interpretation reference prompt. |
| [src/ctg_llm/resources/prompts/quality.txt](src/ctg_llm/resources/prompts/quality.txt) | Separate technical-quality assessment reference prompt. |
| [src/ctg_llm/resources/prompts/ranzcog.txt](src/ctg_llm/resources/prompts/ranzcog.txt) | RANZCOG four-group study encoding reference prompt. |
| [src/ctg_llm/resources/schemas/figo.response.schema.json](src/ctg_llm/resources/schemas/figo.response.schema.json) | FIGO three-category interpretation structured-response contract. |
| [src/ctg_llm/resources/schemas/nice_ng229.response.schema.json](src/ctg_llm/resources/schemas/nice_ng229.response.schema.json) | NICE NG229 interpretation structured-response contract. |
| [src/ctg_llm/resources/schemas/nichd.response.schema.json](src/ctg_llm/resources/schemas/nichd.response.schema.json) | NICHD three-category interpretation structured-response contract. |
| [src/ctg_llm/resources/schemas/parer_ikeda.response.schema.json](src/ctg_llm/resources/schemas/parer_ikeda.response.schema.json) | Parer–Ikeda five-tier interpretation structured-response contract. |
| [src/ctg_llm/resources/schemas/quality.response.schema.json](src/ctg_llm/resources/schemas/quality.response.schema.json) | Separate technical-quality assessment structured-response contract. |
| [src/ctg_llm/resources/schemas/ranzcog.response.schema.json](src/ctg_llm/resources/schemas/ranzcog.response.schema.json) | RANZCOG four-group study encoding structured-response contract. |
| [src/ctg_llm/resources/schemas/render_manifest.schema.json](src/ctg_llm/resources/schemas/render_manifest.schema.json) | Validation schema for the renderer’s parameters, source/image checksums and processing counts. |

## Software checks

| File | Purpose |
| --- | --- |
| [tests/test_contracts.py](tests/test_contracts.py) | Checks of category encodings, strict parsing, JSON schemas, independent requests, retry/refusal rules and audit resumption. |
| [tests/test_rendering.py](tests/test_rendering.py) | Checks of rendering time, FHR masks, gap preservation and parameter/output-name validation. |
| [tests/test_secondary.py](tests/test_secondary.py) | Checks of secondary transformations, partition integrity, probability estimates, paired comparisons and invalid inputs. |

