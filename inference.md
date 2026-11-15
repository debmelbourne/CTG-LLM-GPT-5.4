# Azure inference and fixed parsing

We provide a portable Azure OpenAI interface with one independent technical-quality request and five independent guideline requests for every human-approved image. Only the image and the applicable fixed prompt are included in each request. Outcomes, clinical variables, filenames, study identifiers, quality responses and other guideline responses are not sent as prompt content. Technical-quality results do not determine eligibility.

The public prompt files identify RANZCOG v5.2, NICHD 2008, NICE NG229 with the November 2025 CTG amendment, Parer–Ikeda 2007 and FIGO 2015. They retain the original category scales. The Parer–Ikeda prompt references the published five-tier matrix; the complete copyrighted matrix is not reproduced. The prompts are reusable reference templates; study-specific records are covered by the access arrangements. Alternative authorised prompt/schema files can be supplied as a fixed interface directory; their exact contents and hashes are recorded before requests begin.

## Input and deployment interface

`ctg-llm-infer` accepts a CSV manifest containing exactly `study_id` and `image_path`, or exactly `study_id` and `blob_name`. Each identifier occurs once. Local paths may be absolute or relative to the manifest. Blob names refer to an authorised container. The manifest contains only eligible, de-identified PNG or JPEG image locators; clinical and outcome fields are not accepted. No manifest or image dataset is included in the release.

| Setting | Meaning |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Institutional Azure resource URL or its `/openai/v1/` base URL |
| `AZURE_OPENAI_DEPLOYMENT` | Approved deployment name; recorded as a checksum in the audit configuration |
| `AZURE_STORAGE_ACCOUNT_URL`, `AZURE_STORAGE_CONTAINER` | Required only for Azure Blob image inputs |
| `--model-version` | Exact model identifier expected in the service response, from deployment records |
| `--reasoning-effort` | Fixed reasoning setting for the run |
| `--max-completion-tokens` | Fixed completion token limit, including reasoning tokens |
| `--temperature` | Optional supported sampling setting when reasoning is disabled |
| `--max-attempts` | Total attempts including the first; public default 3 |
| `--image-detail` | Image-detail setting; public default `high` |
| `--timeout` | Request timeout in seconds; public default 120 |
| `--interfaces` | Optional directory containing fixed `prompts/` and `schemas/` files |

Authentication uses Microsoft Entra ID through `DefaultAzureCredential`. The public implementation uses the Azure OpenAI v1 route and the OpenAI Python SDK. No key, endpoint, storage path or institutional configuration is distributed. Model version and inference settings are explicit run inputs.

The command requires `--manifest`, `--output`, `--model-version`, `--reasoning-effort` and `--max-completion-tokens`. `ctg-llm-infer --help` lists all supported options. Deployment identifiers and inference settings are recorded from the executing environment.

## Responses, retries and audit

Each request uses strict JSON Schema. Classification responses contain `guideline`, `raw_category`, `baseline`, `variability`, `accelerations`, `decelerations`, `contractions` and `duration_limitations`. Features may be null when unavailable. A category may be null when the visible image cannot support classification; this remains missing. The quality schema contains only technical observations.

Only transient transport failures and schema-validation failures trigger a repeated, unchanged request. SDK-level retries are disabled. The permitted attempt count is fixed before inference. A valid null category or service refusal does not trigger repeated clinical interpretation. Non-transient service errors or a returned model identifier that differs from the declared version stop execution after audit writing. Responses that remain invalid are retained as missing.

The JSONL audit retains image checksum, task, prompt/schema versions, parser version, declared model/API settings, timestamps, attempt count, full service responses, parsed fields and final status. The service response also records the returned model identifier and token usage. A companion manifest retains the exact prompts and schemas, configuration checksum and software versions. Audit files contain study material and are retained under the applicable data-governance arrangements.

Completed logical requests are resumed by a key containing the image, task, prompt, schema and run-configuration hashes. Terminal missing responses are retained rather than silently rerun. A changed run configuration requires a separate output. A process interruption before a completed logical request is written may require that request to be repeated; the audit is not an exactly-once service guarantee.

## Parsing and analysis hand-off

`ctg-llm parse --input AUDIT_JSONL --output PARSED_CSV` validates classification responses and writes the original category, common tier and status separately. Quality records are excluded. The optional `--wide-output LABEL_CSV` produces `identifier` and the five original label columns for a separate authorised join to study outcomes. No join is performed inside inference or parsing.

The parser rejects unknown fields, duplicate JSON keys, multiple-category text, non-finite values, out-of-range codes and guideline mismatches. It does not infer a category from narrative or use clinical/outcome knowledge to resolve ambiguity. NICHD code 0 is valid. Supplementary Table S1 mapping occurs only after a valid original category is identified.

## Interface references

- [Azure OpenAI structured outputs](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/structured-outputs)
- [Azure reasoning-model parameters](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/reasoning)
- [OpenAI GPT-5.4 model interface](https://developers.openai.com/api/docs/models/gpt-5.4)

These links document the public API interface.
