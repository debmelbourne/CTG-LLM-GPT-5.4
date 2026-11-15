# Software environment

The public reference environment uses the versions below. All selected package releases were published by 31 October 2026. `software_versions.json` records release dates and official Python/PyPI sources. These versions describe the public software environment; historical study execution records follow the data-access arrangements.

| Component | Version |
| --- | --- |
| Python | 3.12.14 |
| NumPy | 2.3.5 |
| pandas | 2.2.3 |
| SciPy | 1.17.0 |
| scikit-learn | 1.8.0 |
| Matplotlib | 3.10.8 |
| openpyxl | 3.1.5 |
| OpenAI Python SDK | 2.54.0 |
| azure-identity | 1.27.0 |
| azure-storage-blob | 12.31.1 |
| jsonschema | 4.26.0 |
| WFDB | 4.3.1 |
| statsmodels | 0.14.6 |
| patsy | 1.0.3 |

`requirements.txt` and `pyproject.toml` pin the direct analysis dependencies. Optional dependency groups are `inference`, `rendering`, `evaluation` and `verification`; their corresponding requirement files record exact versions. `requirements-verified.txt` records the full dependency environment used for the public checks, and `verification_environment.json` provides its machine-readable form.

The secondary-model specification references the following library versions. The public preparation and evaluation modules use the dependencies above; model fitting and protected integration follow the implementation-access arrangements.

| Library referenced by the model specification | Version available by the cutoff |
| --- | --- |
| catboost | 1.2.10 |
| torch | 2.15.0 |
| pytorch-tabnet | 4.1.0 |
| xgboost | 3.4.1 |
| shap | 0.54.1 |
| joblib | 1.5.3 |

Analysis manifests and inference audits record the packages loaded for each run. Azure inference uses the OpenAI v1 route. The deployment name, returned model identifier, reasoning setting and completion-token limit are explicit runtime fields.
