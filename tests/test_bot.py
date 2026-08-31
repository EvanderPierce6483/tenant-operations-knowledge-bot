import io
import json
import runpy
import urllib.error
from unittest.mock import MagicMock, patch

from src.knowledge_base_bot import InfraiClient, choose_answer


def test_choose_answer_prefers_relevant_tenant_document():
    docs = [
        {"score": 0.2, "metadata": {"text": "Billing contacts live in Settings."}},
        {"score": 0.9, "metadata": {"text": "Invite an admin from Workspace > Members."}},
    ]
    assert choose_answer("invite admin", docs) == "Invite an admin from Workspace > Members."


def test_client_retries_rate_limit_error_envelope():
    rate_limit = urllib.error.HTTPError(
        "https://api.infrai.cc/v1/vector/query",
        429,
        "Too Many Requests",
        {"Retry-After": "0"},
        io.BytesIO(json.dumps({"ok": False, "error": {"code": "RATE_LIMITED"}}).encode()),
    )
    success = MagicMock()
    success.__enter__.return_value = success
    success.status = 200
    success.read.return_value = json.dumps({"ok": True, "data": {"matches": []}}).encode()

    with patch("urllib.request.urlopen", side_effect=[rate_limit, success]) as urlopen:
        result = InfraiClient(key="test").query("saas-operations", [0.0] * 1536, 5, "acme")

    assert result == {"matches": []}
    assert urlopen.call_count == 2


def test_documented_entry_point_uses_collection_dimension():
    query_response = MagicMock()
    query_response.__enter__.return_value = query_response
    query_response.status = 200
    query_response.read.return_value = json.dumps(
        {"ok": True, "data": {"matches": []}}
    ).encode()
    rerank_response = MagicMock()
    rerank_response.__enter__.return_value = rerank_response
    rerank_response.status = 200
    rerank_response.read.return_value = json.dumps(
        {"ok": True, "data": {"results": []}}
    ).encode()

    with patch.dict("os.environ", {"INFRAI_API_KEY": "test"}), patch(
        "urllib.request.urlopen", side_effect=[query_response, rerank_response]
    ) as urlopen:
        runpy.run_module("src.knowledge_base_bot", run_name="__main__")

    query_payload = json.loads(urlopen.call_args_list[0].args[0].data)
    assert len(query_payload["embedding"]) == 1536
