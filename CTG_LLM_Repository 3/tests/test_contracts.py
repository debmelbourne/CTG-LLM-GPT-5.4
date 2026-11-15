"""Scalar contract and mocked-service checks; no study or simulated cohort data."""
import json
from pathlib import Path
import tempfile
import unittest
import httpx
from openai import OpenAI
from jsonschema import Draft202012Validator
from ctg_llm.categories import GUIDELINES, common_tier
from ctg_llm.parsing import FEATURES, parse_response, parse_quality
from ctg_llm.inference import (load_interfaces, build_request, classify, read_completed,
                             request_key, azure_url, read_image_manifest)


def category_object(guideline="NICHD", category=0):
    return {"guideline": guideline, "raw_category": category,
            **{field: None for field in FEATURES}}


def service_response(content, *, refusal=None, finish_reason="stop"):
    return {"id": "contract-check", "object": "chat.completion", "created": 0,
            "model": "mock-model", "choices": [{"index": 0,
            "finish_reason": finish_reason, "message": {
                "role": "assistant", "content": content, "refusal": refusal}}],
            "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.interfaces = load_interfaces()
        cls.settings = {"reasoning_effort": "none", "max_completion_tokens": 100,
                        "image_detail": "high", "max_attempts": 3, "temperature": 0}

    def call_mock(self, responses, task="NICHD"):
        calls, waits = [], []
        def handler(request):
            calls.append(json.loads(request.content))
            status, body = responses[min(len(calls)-1, len(responses)-1)]
            return httpx.Response(status, json=body)
        with OpenAI(api_key="unit-test", base_url="https://unit.invalid/openai/v1/",
                    max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
            result = classify(client, b"\x89PNG\r\n\x1a\n", task, self.interfaces[task],
                              self.settings, "unit-deployment", sleep=waits.append)
        return result, calls, waits

    def test_all_category_mappings(self):
        expected = {"RANZCOG": [1,2,2,3], "NICHD": [1,2,3], "NICE/RCOG": [1,2,3],
                    "Parer-Ikeda": [1,1,2,3,3], "FIGO": [1,2,3]}
        for guideline, spec in GUIDELINES.items():
            self.assertEqual([common_tier(guideline, x) for x in spec["codes"]], expected[guideline])

    def test_nichd_zero_is_valid(self):
        result = parse_response(category_object(), "NICHD")
        self.assertEqual((result.raw_category, result.common_tier, result.status), (0,1,"parsed"))

    def test_every_raw_code_matches_schema_and_parser(self):
        for name, spec in GUIDELINES.items():
            for code in spec["codes"]:
                value = category_object(name, code)
                self.assertTrue(Draft202012Validator(self.interfaces[name]["schema"]).is_valid(value))
                self.assertEqual(parse_response(value, name).raw_category, code)

    def test_nullable_category_preserves_missing(self):
        result = parse_response(category_object(category=None), "NICHD")
        self.assertEqual(result.status, "missing_category")
        self.assertIsNone(result.common_tier)

    def test_boolean_and_string_categories_rejected(self):
        for value in (True, False, "0", "I", [0], 0.5, 9):
            self.assertIsNone(parse_response(category_object(category=value), "NICHD").raw_category)

    def test_duplicate_keys_rejected(self):
        value = json.dumps(category_object()).replace('"raw_category": 0', '"raw_category": 0, "raw_category": 2')
        self.assertEqual(parse_response(value, "NICHD").status, "invalid_json")

    def test_extra_field_rejected(self):
        value = category_object(); value["outcome"] = 1
        self.assertEqual(parse_response(value, "NICHD").status, "invalid_schema")

    def test_guideline_mismatch_rejected(self):
        self.assertEqual(parse_response(category_object("FIGO", 1), "NICHD").status, "invalid_schema")

    def test_narrative_not_reinterpreted(self):
        self.assertIsNone(parse_response("Category I or II", "NICHD").raw_category)

    def test_feature_type_checked(self):
        value = category_object(); value["baseline"] = 140
        self.assertEqual(parse_response(value, "NICHD").status, "invalid_schema")

    def test_nonfinite_json_rejected(self):
        value = json.dumps(category_object()).replace('"raw_category": 0', '"raw_category": NaN')
        self.assertEqual(parse_response(value, "NICHD").status, "invalid_json")

    def test_quality_cannot_add_eligibility(self):
        value = {"fhr_visible": None, "uterine_activity_visible": None,
                 "duration_limitations": None, "quality_limitations": None}
        self.assertEqual(parse_quality(value)[1], "parsed")
        value["eligible"] = True
        self.assertEqual(parse_quality(value)[1], "invalid_schema")

    def test_all_schemas_valid(self):
        self.assertEqual(set(self.interfaces), {"quality", *GUIDELINES})
        for item in self.interfaces.values():
            Draft202012Validator.check_schema(item["schema"])
            self.assertNotIn("{{", item["prompt"])
            self.assertEqual(set(item["schema"]["required"]), set(item["schema"]["properties"]))

    def test_six_isolated_request_bodies(self):
        for task, interface in self.interfaces.items():
            request = build_request(b"\x89PNG\r\n\x1a\n", task, interface, self.settings, "deployment")
            self.assertEqual(len(request["messages"]), 1)
            self.assertEqual(len(request["messages"][0]["content"]), 2)
            self.assertEqual(request["messages"][0]["content"][0]["text"], interface["prompt"])
            self.assertTrue(request["response_format"]["json_schema"]["strict"])
            self.assertFalse(request["store"])
            self.assertNotIn("study_id", request)

    def test_transient_retry_is_unchanged(self):
        good = service_response(json.dumps(category_object()))
        result, calls, waits = self.call_mock([(503, {"error": {"message": "temporary"}}), (200, good)])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["attempt_count"], 2)
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(waits, [1])

    def test_schema_retry_is_unchanged(self):
        result, calls, _ = self.call_mock([(200, service_response("not-json")),
                                         (200, service_response(json.dumps(category_object())))])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(calls[0], calls[1])

    def test_exhausted_schema_failure_is_missing(self):
        result, calls, _ = self.call_mock([(200, service_response('{}'))])
        self.assertEqual(len(calls), 3)
        self.assertEqual(result["status"], "invalid_schema")
        self.assertIsNone(result["parsed"])

    def test_null_category_is_not_retried(self):
        result, calls, _ = self.call_mock([(200, service_response(json.dumps(category_object(category=None))))])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "missing_category")

    def test_refusal_is_not_retried(self):
        result, calls, _ = self.call_mock([(200, service_response(None, refusal="refused"))])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "refused")
        self.assertIsNone(result["parsed"])

    def test_truncated_completion_is_missing(self):
        result, calls, _ = self.call_mock([(200, service_response(json.dumps(category_object()), finish_reason="length"))])
        self.assertEqual(len(calls), 3)
        self.assertIsNone(result["parsed"])

    def test_nontransient_error_is_not_retried(self):
        result, calls, _ = self.call_mock([(400, {"error": {"message": "bad request"}})])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["status"], "service_failure")

    def test_unexpected_model_is_missing_without_retry(self):
        original = self.settings
        self.settings = {**original, "declared_model_version": "expected-model"}
        try:
            result, calls, _ = self.call_mock([(200, service_response(json.dumps(category_object())))])
            self.assertEqual(len(calls), 1)
            self.assertEqual(result["status"], "model_mismatch")
            self.assertIsNone(result["parsed"])
        finally:
            self.settings = original

    def test_request_key_changes_with_image_or_prompt(self):
        item = self.interfaces["NICHD"]
        initial = request_key("id", "hash-a", "NICHD", item, "configuration")
        self.assertNotEqual(initial, request_key("id", "hash-b", "NICHD", item, "configuration"))
        self.assertNotEqual(initial, request_key("id", "hash-a", "NICHD", {**item, "prompt_version": "different"}, "configuration"))

    def test_resume_validates_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"audit.jsonl"
            path.write_text(json.dumps({"request_key": "key", "configuration_sha256": "config",
                                        "study_id": "id", "image_sha256": "hash"})+'\n')
            self.assertEqual(read_completed(path, "config"), ({"key"}, {"id": "hash"}))
            with self.assertRaises(ValueError): read_completed(path, "changed")

    def test_manifest_rejects_clinical_columns(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/"header.csv"
            path.write_text("study_id,image_path,outcome\n")
            with self.assertRaises(ValueError): read_image_manifest(path)

    def test_azure_url_normalisation(self):
        self.assertEqual(azure_url("https://unit.openai.azure.com"), "https://unit.openai.azure.com/openai/v1/")
        self.assertEqual(azure_url("https://unit.openai.azure.com/openai/v1/"), "https://unit.openai.azure.com/openai/v1/")
        with self.assertRaises(ValueError): azure_url("http://unit.openai.azure.com")
        with self.assertRaises(ValueError): azure_url("https://unit.openai.azure.com/other")


if __name__ == "__main__":
    unittest.main()
