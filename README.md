# CTG-LLM-GPT-5.4
Reproducibility and code package
# CTG LLM reproducibility resources

We provide public software and method specifications accompanying **GPT classification of cardiotocography across five international guidelines shows second reader potential for fetal asphyxia in two cohorts on different continents**, by Debjyoti Karmakar, Erica Spessot, Enes Makalic and Fiona Brownfoot.

The study evaluated OpenAI GPT-5.4 through Azure OpenAI Service. Repository and package names are model-neutral.

The workflow consists of one technical-quality request and five independent guideline-classification requests for each human-approved CTG image. Structured responses retain each guideline's original category. A separate three-tier mapping follows Supplementary Table S1. Primary discrimination analyses use the original categories directly.

| Component | Public resource |
| --- | --- |
| Azure requests, audit logging and parsing | `inference.py`, `parsing.py`, prompt files and JSON schemas |
| Primary and sensitivity analyses | `analysis.py`, `statistics.py`, `cohorts.py`, `outcomes.py` and `plots.py` |
| Secondary predictor preparation and partitioning | `secondary.py` |
| Evaluation of existing probability predictions | `probability_metrics.py` |
| CTU-UHB signal-to-image rendering | `scripts/render_ctu_signals.py` and `rendering.py` |
| Complete file descriptions | [Contents](CONTENTS.md) |
| Relationship to the six source scripts | [Script coverage](docs/script_coverage.md) |
| Input fields and analysis interfaces | [Analysis](docs/analysis.md) and [Secondary modelling](docs/secondary_model.md) |
| Guideline editions, inference and rendering methods | [Guidelines](docs/guidelines.md), [Inference](docs/inference.md) and [Rendering](docs/rendering.md) |
| Software versions and checks | [Environment](environment/README.md) and [Verification](VERIFICATION.md) |
| Access and implementation scope | [Availability](CODE_AND_DATA_AVAILABILITY.md) and [Reproducibility](docs/reproducibility.md) |

The package supports Python 3.12.14. `pip install '.[inference,rendering,evaluation]'` installs the public analysis, Azure inference, WFDB rendering and probability-evaluation dependencies. `environment/requirements-verified.txt` records the complete verification environment. The named package releases were available by 31 October 2026; release dates and official sources are recorded in `environment/software_versions.json`.

The `ctg-llm` interface exposes `analyse`, `parse`, `prepare-secondary` and `evaluate-probabilities`. `ctg-llm-infer` provides Azure inference. The executable renderer is `scripts/render_ctu_signals.py`. Their help interfaces describe runtime inputs and options.

The public secondary-model functions cover predictor preparation, partitioning and evaluation of existing predictions. The model-combination specification is provided separately; fitted learners and protected integration components follow the access arrangements.

No real or simulated datasets, CTG images, study responses, fitted models or results tables are distributed. Study-specific data require a request to the corresponding authors. The article and Supplementary Information report the study results.
