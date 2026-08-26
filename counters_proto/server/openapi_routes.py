"""OpenAPI 3 spec + Swagger UI for the counters-mint REST API.

Serves:
  GET /openapi.json  — the machine-readable OpenAPI 3.0 document
  GET /docs          — a Swagger UI page (loads swagger-ui from a CDN)

The spec is built by hand (the server is a stdlib http.server, no framework to
introspect) but kept in sync with the mint/ai route handlers. It documents the
browser-wallet mint flow (prepare -> reveal -> broadcast -> status) and the AI
assist routes, so agents (and the counters-mint REST skill) can drive the API.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler


def build_spec(network: str = "mainnet") -> dict:
    """Return the OpenAPI 3.0 document as a dict."""
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Bitcoin Counters — Mint API",
            "version": "0.1.0",
            "description": (
                "Browser-wallet minting of Bitcoin Counters (Counterparty-backed "
                "numbered inscriptions). PSBT-based: the server builds unsigned "
                "transactions, the wallet signs, the server finalizes and "
                "broadcasts. Supports mainnet / testnet4 / signet via BTC_NETWORK."
            ),
        },
        "servers": [{"url": "/", "description": f"active network: {network}"}],
        "paths": {
            "/status": {
                "get": {
                    "summary": "Server + network status",
                    "operationId": "getStatus",
                    "responses": {"200": {"description": "OK", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/mint/prepare": {
                "post": {
                    "summary": "Build the inscription + commit address",
                    "operationId": "mintPrepare",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PrepareRequest"}}}},
                    "responses": {"200": {"description": "Prepared", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/PrepareResponse"}}}}},
                }
            },
            "/mint/reveal": {
                "post": {
                    "summary": "Build the reveal PSBT (server pre-signs vin[1])",
                    "operationId": "mintReveal",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/RevealRequest"}}}},
                    "responses": {"200": {"description": "Reveal PSBT ready", "content": {"application/json": {"schema": {"type": "object"}}}}},
                }
            },
            "/mint/broadcast": {
                "post": {
                    "summary": "Finalize the wallet-signed PSBT and broadcast",
                    "operationId": "mintBroadcast",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BroadcastRequest"}}}},
                    "responses": {"200": {"description": "Broadcast", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BroadcastResponse"}}}}},
                }
            },
            "/mint/status/{session_id}": {
                "get": {
                    "summary": "Poll mint session status + counter number",
                    "operationId": "mintStatus",
                    "parameters": [{"name": "session_id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "Status", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/StatusResponse"}}}}},
                }
            },
            "/ai/fee-advice": {
                "get": {
                    "summary": "Mempool fee tiers + AI recommendation",
                    "operationId": "aiFeeAdvice",
                    "responses": {"200": {"description": "OK"}, "503": {"description": "AI unavailable (GEMINI_API_KEY unset)"}},
                }
            },
            "/ai/mint-parse": {
                "post": {
                    "summary": "Natural language -> mint params",
                    "operationId": "aiMintParse",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object", "properties": {"prompt": {"type": "string"}}}}}},
                    "responses": {"200": {"description": "OK"}, "503": {"description": "AI unavailable"}},
                }
            },
            "/ai/name-suggest": {
                "post": {
                    "summary": "File content -> asset-name suggestions",
                    "operationId": "aiNameSuggest",
                    "requestBody": {"required": True, "content": {"application/json": {"schema": {"type": "object"}}}},
                    "responses": {"200": {"description": "OK"}, "503": {"description": "AI unavailable"}},
                }
            },
            "/counters": {"get": {"summary": "List indexed counters", "operationId": "listCounters", "responses": {"200": {"description": "OK"}}}},
            "/counter/{id}": {
                "get": {
                    "summary": "One counter by id/asset",
                    "operationId": "getCounter",
                    "parameters": [{"name": "id", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}, "404": {"description": "Not found"}},
                }
            },
        },
        "components": {
            "schemas": {
                "PrepareRequest": {
                    "type": "object",
                    "required": ["content_type", "body_b64", "supply", "divisible", "fee_rate", "wallet_address"],
                    "properties": {
                        "content_type": {"type": "string", "example": "image/png"},
                        "body_b64": {"type": "string", "description": "base64 inscription body"},
                        "supply": {"type": "integer"},
                        "divisible": {"type": "boolean"},
                        "fee_rate": {"type": "number", "description": "sat/vB"},
                        "wallet_address": {"type": "string"},
                    },
                },
                "PrepareResponse": {
                    "type": "object",
                    "properties": {
                        "session_id": {"type": "string"},
                        "commit_address": {"type": "string"},
                        "commit_value_sats": {"type": "integer"},
                        "min_source_sats": {"type": "integer"},
                        "asset": {"type": "string"},
                        "network": {"type": "string", "enum": ["mainnet", "testnet4", "signet"]},
                        "explorer_base": {"type": "string"},
                    },
                },
                "RevealRequest": {"type": "object", "required": ["session_id"], "properties": {"session_id": {"type": "string"}}},
                "BroadcastRequest": {"type": "object", "required": ["session_id", "signed_psbt"], "properties": {"session_id": {"type": "string"}, "signed_psbt": {"type": "string"}}},
                "BroadcastResponse": {"type": "object", "properties": {"reveal_txid": {"type": "string"}}},
                "StatusResponse": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "reveal_txid": {"type": "string", "nullable": True},
                        "counter_number": {"type": "integer", "nullable": True},
                        "asset": {"type": "string"},
                    },
                },
            }
        },
    }


_SWAGGER_HTML = """<!doctype html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>Bitcoin Counters — API docs</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.ui = SwaggerUIBundle({ url: '/openapi.json', dom_id: '#swagger-ui' });
  </script>
</body>
</html>"""


def handle_openapi(handler: BaseHTTPRequestHandler, path: str, method: str, network: str = "mainnet") -> bool:
    """Serve /openapi.json and /docs. Returns True if the request was handled."""
    if method != "GET":
        return False
    if path == "/openapi.json":
        body = json.dumps(build_spec(network)).encode()
        handler.send_response(200)
        handler.send_header("Content-Type", "application/json; charset=utf-8")
        handler.send_header("Access-Control-Allow-Origin", "*")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
        return True
    if path == "/docs":
        body = _SWAGGER_HTML.encode()
        handler.send_response(200)
        handler.send_header("Content-Type", "text/html; charset=utf-8")
        handler.send_header("Content-Length", str(len(body)))
        handler.end_headers()
        handler.wfile.write(body)
        return True
    return False
