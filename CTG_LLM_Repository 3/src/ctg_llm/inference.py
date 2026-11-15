"""Independent Azure OpenAI image requests with versioned structured responses.

Public reference implementation. Institutional endpoint and deployment settings
are external inputs; no study images or credentials are included.
"""
import argparse
import base64
import csv
from dataclasses import asdict
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from pathlib import Path
import hashlib
import json
import os
import time
from urllib.parse import urlparse

from . import __version__
from .categories import GUIDELINES
from .parsing import (PARSER_VERSION, decode_response, parse_quality,
                      parse_response)

TASK_FILES = {
    "quality": "quality", "RANZCOG": "ranzcog", "NICHD": "nichd",
    "NICE/RCOG": "nice_ng229", "Parer-Ikeda": "parer_ikeda", "FIGO": "figo",
}


def digest(value):
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def software_versions():
    import platform
    result = {"python": platform.python_version(), "ctg_llm": __version__}
    for name in ("openai", "azure-identity", "azure-storage-blob", "jsonschema"):
        try:
            result[name] = version(name)
        except PackageNotFoundError:
            result[name] = None
    return result


def load_interfaces(directory=None):
    """Load and freeze all six prompt/schema pairs before any image request."""
    from jsonschema import Draft202012Validator
    root = Path(directory) if directory else files("ctg_llm").joinpath("resources")
    result = {}
    for task, stem in TASK_FILES.items():
        prompt = root.joinpath("prompts", stem + ".txt").read_text(encoding="utf-8")
        schema = json.loads(root.joinpath("schemas", stem + ".response.schema.json").read_text(encoding="utf-8"))
        if not prompt.strip() or "{{" in prompt:
            raise ValueError("Each inference prompt must be complete")
        Draft202012Validator.check_schema(schema)
        if schema.get("additionalProperties") is not False:
            raise ValueError("Response schemas must prohibit additional fields")
        result[task] = {"prompt": prompt, "schema": schema,
                        "prompt_version": digest(prompt),
                        "schema_version": digest(canonical(schema))}
    return result


def read_image_manifest(path):
    """Accept only an opaque study ID and an image locator; never outcomes."""
    path = Path(path)
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        columns = reader.fieldnames or []
        if len(columns) != 2 or set(columns) not in (
                {"study_id", "image_path"}, {"study_id", "blob_name"}):
            raise ValueError("Image manifest requires exactly study_id and image_path or blob_name")
        locator = "image_path" if "image_path" in columns else "blob_name"
        rows = list(reader)
    seen = set()
    for row in rows:
        if set(row) != set(columns) or any(not isinstance(row[k], str) or not row[k].strip() for k in columns):
            raise ValueError("Incomplete image-manifest row")
        if row["study_id"] in seen:
            raise ValueError("Duplicate study_id in image manifest")
        seen.add(row["study_id"])
        if Path(row[locator]).suffix.lower() not in (".png", ".jpg", ".jpeg"):
            raise ValueError("Image inputs must be PNG or JPEG")
        if locator == "image_path":
            image = Path(row[locator])
            if not image.is_absolute():
                image = path.parent / image
            row[locator] = str(image.resolve())
    if not rows:
        raise ValueError("Image manifest is empty")
    return rows, locator


def image_mime(image_bytes):
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    raise ValueError("Image bytes are not PNG or JPEG")


def build_request(image_bytes, task, interface, settings, deployment):
    """Construct a fresh one-image request with no conversational history."""
    schema = {k: v for k, v in interface["schema"].items()
              if k not in ("$schema", "title")}
    encoded = base64.b64encode(image_bytes).decode("ascii")
    request = {
        "model": deployment,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": interface["prompt"]},
            {"type": "image_url", "image_url": {
                "url": "data:" + image_mime(image_bytes) + ";base64," + encoded,
                "detail": settings["image_detail"],
            }},
        ]}],
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "ctg_llm_" + TASK_FILES[task], "strict": True, "schema": schema}},
        "reasoning_effort": settings["reasoning_effort"],
        "max_completion_tokens": settings["max_completion_tokens"],
        "store": False,
    }
    if settings.get("temperature") is not None:
        request["temperature"] = settings["temperature"]
    return request


def interpret_completion(completion, task, interface):
    """A refusal or a valid null category is terminal, not a retry trigger."""
    from jsonschema import Draft202012Validator
    choices = completion.choices
    if len(choices) != 1:
        return None, None, "invalid_schema"
    choice = choices[0]
    message = choice.message
    raw = message.content
    if message.refusal or choice.finish_reason == "content_filter":
        return raw, None, "refused"
    if choice.finish_reason != "stop":
        return raw, None, "invalid_schema"
    try:
        value = decode_response(raw)
        if not Draft202012Validator(interface["schema"]).is_valid(value):
            return raw, None, "invalid_schema"
        if task == "quality":
            parsed, status = parse_quality(value)
        else:
            parsed = asdict(parse_response(value, task))
            status = parsed["status"]
        return raw, parsed, status
    except (ValueError, TypeError):
        return raw, None, "invalid_json"


def is_transient(error):
    """Transport failures only; non-transient service errors are terminal."""
    from openai import APIConnectionError, APITimeoutError, APIStatusError
    if isinstance(error, (APIConnectionError, APITimeoutError)):
        return True
    return isinstance(error, APIStatusError) and (
        error.status_code in (408, 409, 429) or error.status_code >= 500)


def classify(client, image_bytes, task, interface, settings, deployment,
             *, sleep=time.sleep):
    """Retry unchanged requests only for transport or response-schema failure."""
    from openai import APIError
    request = build_request(image_bytes, task, interface, settings, deployment)
    attempts, raw, parsed, status = [], None, None, "missing"
    for number in range(1, settings["max_attempts"] + 1):
        raw, parsed = None, None
        start = time.monotonic()
        entry = {"attempt": number, "timestamp_utc": utc_now()}
        retry = False
        try:
            completion = client.chat.completions.create(**request)
            raw, parsed, status = interpret_completion(completion, task, interface)
            if settings.get("declared_model_version") and completion.model != settings["declared_model_version"]:
                parsed, status = None, "model_mismatch"
            entry.update(raw_response=completion.model_dump(mode="json"), status=status)
            retry = status in ("invalid_schema", "invalid_json", "invalid_category")
        except APIError as error:
            retry = is_transient(error)
            status = "transport_failure" if retry else "service_failure"
            # Error strings can contain private endpoint details.
            entry.update(status=status, error_type=type(error).__name__,
                         http_status=getattr(error, "status_code", None))
        entry["elapsed_seconds"] = time.monotonic() - start
        attempts.append(entry)
        if not retry or number == settings["max_attempts"]:
            break
        sleep(min(2 ** (number - 1), 30))
    # A failed final request must not retain a category from any earlier attempt.
    if status not in ("parsed", "missing_category"):
        parsed = None
    return {"response": raw, "parsed": parsed, "status": status,
            "attempt_count": len(attempts), "attempts": attempts}


def request_key(study_id, image_hash, task, interface, configuration_hash):
    return digest(canonical({"study_id": study_id, "image_sha256": image_hash,
                            "task": task, "prompt_version": interface["prompt_version"],
                            "schema_version": interface["schema_version"],
                            "configuration_sha256": configuration_hash}))


def read_completed(path, configuration_hash):
    """Completed logical requests, including terminal missing results, are retained."""
    completed, known_images = set(), {}
    if not Path(path).exists():
        return completed, known_images
    with open(path, encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except ValueError as error:
                raise ValueError("Audit contains an incomplete JSON line") from error
            if record.get("configuration_sha256") != configuration_hash:
                raise ValueError("Audit configuration differs; a separate output is required")
            key = record.get("request_key")
            if not isinstance(key, str) or not key or key in completed:
                raise ValueError("Invalid or duplicate request key in audit")
            completed.add(key)
            identifier, image_hash = record.get("study_id"), record.get("image_sha256")
            if not isinstance(identifier, str) or not isinstance(image_hash, str):
                raise ValueError("Audit image identity is missing")
            if identifier in known_images and known_images[identifier] != image_hash:
                raise ValueError("Audit contains different images for one study ID")
            known_images[identifier] = image_hash
    return completed, known_images


def required_env(name):
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError("Required environment setting is absent: " + name)
    return value


def azure_url(endpoint):
    parsed = urlparse(endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("Azure endpoint must be an HTTPS resource URL")
    if parsed.path.rstrip("/") not in ("", "/openai/v1"):
        raise ValueError("Azure endpoint must be the resource root or /openai/v1/")
    return endpoint.rstrip("/") + ("/" if parsed.path.rstrip("/") else "/openai/v1/")


def run(args):
    from azure.identity import DefaultAzureCredential, get_bearer_token_provider
    from openai import OpenAI
    images, locator = read_image_manifest(args.manifest)
    interfaces = load_interfaces(args.interfaces)
    endpoint = azure_url(required_env("AZURE_OPENAI_ENDPOINT"))
    deployment = required_env("AZURE_OPENAI_DEPLOYMENT")
    settings = {"declared_model_version": args.model_version, "api_version": "v1",
                "reasoning_effort": args.reasoning_effort,
                "max_completion_tokens": args.max_completion_tokens,
                "temperature": args.temperature, "image_detail": args.image_detail,
                "max_attempts": args.max_attempts, "timeout_seconds": args.timeout,
                "sdk_max_retries": 0, "parser_version": PARSER_VERSION}
    configuration = {"settings": settings, "package_version": __version__,
                     "deployment_sha256": digest(deployment),
                     "endpoint_sha256": digest(endpoint),
                     "environment": software_versions(),
                     "interfaces": interfaces,
                     "image_manifest_sha256": digest(Path(args.manifest).read_bytes())}
    configuration_hash = digest(canonical(configuration))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = output.with_name(output.name + ".manifest.json")
    if manifest_path.exists():
        prior = json.loads(manifest_path.read_text())
        if prior.get("configuration_sha256") != configuration_hash:
            raise ValueError("Existing inference run has a different configuration")
    elif output.exists() and output.stat().st_size:
        raise ValueError("Audit manifest is absent")
    else:
        with manifest_path.open("x", encoding="utf-8") as stream:
            json.dump({"created_utc": utc_now(), "configuration_sha256": configuration_hash,
                       **configuration}, stream, indent=2, allow_nan=False)
            stream.write("\n")
    completed, known_images = read_completed(output, configuration_hash)
    credential = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    token_provider = get_bearer_token_provider(credential, "https://ai.azure.com/.default")
    client = OpenAI(base_url=endpoint, api_key=token_provider,
                    max_retries=0, timeout=args.timeout)
    storage = None
    try:
        if locator == "blob_name":
            from azure.storage.blob import BlobServiceClient
            storage = BlobServiceClient(required_env("AZURE_STORAGE_ACCOUNT_URL"),
                                        credential=credential, retry_total=0)
            container = required_env("AZURE_STORAGE_CONTAINER")
        with output.open("a", encoding="utf-8") as stream:
            for row in images:
                if locator == "image_path":
                    image_bytes = Path(row[locator]).read_bytes()
                else:
                    image_bytes = storage.get_blob_client(container, row[locator]).download_blob().readall()
                image_mime(image_bytes)
                image_hash = digest(image_bytes)
                if row["study_id"] in known_images and known_images[row["study_id"]] != image_hash:
                    raise ValueError("Image content changed within an existing inference run")
                # Quality is descriptive; its status never gates guideline requests.
                for task, interface in interfaces.items():
                    key = request_key(row["study_id"], image_hash, task, interface, configuration_hash)
                    if key in completed:
                        continue
                    result = classify(client, image_bytes, task, interface, settings, deployment)
                    record = {"study_id": row["study_id"], "task": task,
                              "guideline": None if task == "quality" else task,
                              "image_sha256": image_hash, "request_key": key,
                              "configuration_sha256": configuration_hash,
                              "prompt_version": interface["prompt_version"],
                              "schema_version": interface["schema_version"],
                              "parser_version": PARSER_VERSION,
                              "timestamp_utc": utc_now(), **settings, **result}
                    stream.write(json.dumps(record, allow_nan=False) + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                    completed.add(key)
                    if result["status"] in ("service_failure", "model_mismatch"):
                        raise ValueError("Azure service or model-version mismatch; audit retained")
    finally:
        client.close()
        if storage is not None:
            storage.close()
        credential.close()


def main():
    parser = argparse.ArgumentParser(description="Azure CTG research inference: separate quality and five guideline requests")
    parser.add_argument("--manifest", required=True, help="Authorised image-manifest CSV")
    parser.add_argument("--output", required=True, help="Governed JSONL audit path")
    parser.add_argument("--model-version", required=True, help="Exact expected model identifier in the service response")
    parser.add_argument("--reasoning-effort", required=True, choices=("none", "low", "medium", "high", "xhigh"))
    parser.add_argument("--max-completion-tokens", required=True, type=int)
    parser.add_argument("--temperature", type=float, help="Optional sampling setting when reasoning is none")
    parser.add_argument("--max-attempts", type=int, default=3, help="Total attempts per logical request, including the first")
    parser.add_argument("--image-detail", choices=("high", "low", "auto"), default="high")
    parser.add_argument("--timeout", type=float, default=120)
    parser.add_argument("--interfaces", help="Alternative fixed directory containing prompts/ and schemas/")
    args = parser.parse_args()
    if not args.model_version.strip() or args.max_attempts < 1 or args.max_completion_tokens < 1 or args.timeout <= 0:
        parser.error("Version, token limit, attempt limit and timeout must be specified and positive")
    if args.temperature is not None and (args.reasoning_effort != "none" or not 0 <= args.temperature <= 2):
        parser.error("Temperature must be 0–2 and is supported here only with reasoning-effort none")
    try:
        run(args)
    except ImportError as error:
        parser.exit(2, "Inference dependencies are unavailable; the inference optional dependency group is required.\n")
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + "\n")


if __name__ == "__main__":
    main()
