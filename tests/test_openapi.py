"""The OpenAPI spec must be valid-ish and cover the documented endpoints."""

from __future__ import annotations

import json

from counters_proto.server.openapi_routes import build_spec


def test_spec_is_openapi_3():
    spec = build_spec()
    assert spec["openapi"].startswith("3.")
    assert spec["info"]["title"]
    assert "paths" in spec


def test_documents_mint_flow():
    paths = build_spec()["paths"]
    for p in ("/mint/prepare", "/mint/reveal", "/mint/broadcast", "/mint/status/{session_id}"):
        assert p in paths, f"missing {p}"


def test_documents_ai_routes():
    paths = build_spec()["paths"]
    for p in ("/ai/fee-advice", "/ai/mint-parse", "/ai/name-suggest"):
        assert p in paths


def test_network_flows_into_servers():
    spec = build_spec("testnet4")
    assert "testnet4" in spec["servers"][0]["description"]


def test_spec_is_json_serializable():
    # The route handler serializes this; ensure no non-JSON types slipped in.
    json.dumps(build_spec())


def test_prepare_response_schema_matches_server_fields():
    props = build_spec()["components"]["schemas"]["PrepareResponse"]["properties"]
    for field in ("session_id", "commit_address", "network", "explorer_base"):
        assert field in props
