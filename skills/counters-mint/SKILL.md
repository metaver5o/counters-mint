---
name: counters-mint
description: Drive the counters-mint REST API — mint Bitcoin Counters (Counterparty-backed numbered inscriptions) via the browser-wallet PSBT flow, query indexed counters, and use the AI assist routes. Use when an agent needs to prepare/reveal/broadcast a counter mint, poll mint status, list/inspect counters, or fetch fee advice from a running counters-mint server.
---

# counters-mint REST skill

Wraps the counters-mint HTTP API. The server publishes a live OpenAPI 3 spec at
`GET /openapi.json` (Swagger UI at `/docs`) — always prefer that for the exact,
current shapes. This skill summarizes the flow and ships a stdlib client.

- Base URL: the running server (default `http://127.0.0.1:8082`); override with
  `COUNTERS_BASE_URL`.
- Networks: mainnet / testnet4 / signet (server-side `BTC_NETWORK`). The
  `/mint/prepare` response echoes `network` + `explorer_base`.

## Mint flow (browser-wallet PSBT)

1. `POST /mint/prepare` `{content_type, body_b64, supply, divisible, fee_rate,
   wallet_address}` -> `{session_id, commit_address, commit_value_sats,
   min_source_sats, asset, network, explorer_base}`. Wallet then sends dust to
   `commit_address`.
2. `POST /mint/reveal` `{session_id, ...commit/source utxo...}` -> reveal PSBT
   (server pre-signs its input; the wallet signs the funding input).
3. `POST /mint/broadcast` `{session_id, signed_psbt}` -> `{reveal_txid}`.
4. `GET /mint/status/{session_id}` -> `{status, reveal_txid, counter_number, asset}`.

Signing happens in the browser wallet; this skill orchestrates the server calls.

## Read + AI

- `GET /status` — server + network status.
- `GET /counters` — list indexed counters.
- `GET /counter/{id}` — one counter by id/asset.
- `GET /ai/fee-advice` — mempool tiers + AI fee recommendation (503 if no key).
- `POST /ai/mint-parse` `{prompt}` — natural language -> mint params.
- `POST /ai/name-suggest` — content -> asset-name suggestions.

## Client

`scripts/counters.py` (stdlib only):

```bash
python3 scripts/counters.py openapi                 # dump the live spec
python3 scripts/counters.py status
python3 scripts/counters.py counters --limit 20
python3 scripts/counters.py counter A1234567890
python3 scripts/counters.py fee-advice
python3 scripts/counters.py get /mint/status/<sid>  # raw GET passthrough
```

Set `COUNTERS_BASE_URL` to point at a non-default server.

## Guidance

- Always read `/openapi.json` first for authoritative shapes; this doc can lag.
- Minting requires a browser wallet to sign; a headless agent can prepare and
  poll but cannot produce the wallet signature.
- Respect the active network from the prepare response for explorer links.
