#!/usr/bin/env python3
"""Stdlib client + CLI for the counters-mint REST API.

No third-party deps. Base URL from COUNTERS_BASE_URL (default 127.0.0.1:8082).
The server's /openapi.json is the source of truth for shapes.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = os.environ.get("COUNTERS_BASE_URL", "http://127.0.0.1:8082").rstrip("/")
TIMEOUT = 30


def _req(method: str, path: str, body: dict | None = None) -> dict:
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} {method} {url}\n{e.read().decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"request failed {method} {url}: {e.reason}")


def _emit(obj) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description="counters-mint REST client")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("openapi", help="dump /openapi.json")
    sub.add_parser("status", help="GET /status")
    sub.add_parser("fee-advice", help="GET /ai/fee-advice")
    c = sub.add_parser("counters", help="GET /counters")
    c.add_argument("--limit", type=int)
    one = sub.add_parser("counter", help="GET /counter/<id>")
    one.add_argument("id")
    st = sub.add_parser("mint-status", help="GET /mint/status/<session_id>")
    st.add_argument("session_id")
    g = sub.add_parser("get", help="raw GET passthrough")
    g.add_argument("path")
    args = p.parse_args(argv)

    if args.cmd == "openapi":
        _emit(_req("GET", "/openapi.json"))
    elif args.cmd == "status":
        _emit(_req("GET", "/status"))
    elif args.cmd == "fee-advice":
        _emit(_req("GET", "/ai/fee-advice"))
    elif args.cmd == "counters":
        q = f"?limit={args.limit}" if args.limit else ""
        _emit(_req("GET", "/counters" + q))
    elif args.cmd == "counter":
        _emit(_req("GET", "/counter/" + urllib.parse.quote(args.id, safe="")))
    elif args.cmd == "mint-status":
        _emit(_req("GET", "/mint/status/" + urllib.parse.quote(args.session_id, safe="")))
    elif args.cmd == "get":
        _emit(_req("GET", args.path if args.path.startswith("/") else "/" + args.path))


if __name__ == "__main__":
    main()
