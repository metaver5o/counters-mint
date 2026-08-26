# counters-mint API reference

The running server serves the authoritative spec at `GET /openapi.json` (Swagger
UI at `/docs`). This file is a quick reference; when they disagree, trust
`/openapi.json`.

Base URL: `COUNTERS_BASE_URL` (default `http://127.0.0.1:8082`). JSON in/out.
Networks: mainnet / testnet4 / signet (`BTC_NETWORK`).

## Mint (browser-wallet PSBT)

### POST /mint/prepare
Body: `{content_type, body_b64, supply, divisible, fee_rate, wallet_address}`
Returns: `{session_id, commit_address, commit_value_sats, min_source_sats,
asset, network, explorer_base}`

### POST /mint/reveal
Body: `{session_id, commit_txid, source_utxo:{txid, vout, value, script_pubkey_hex}}`
Returns `{reveal_psbt_hex}` for the wallet to sign (server pre-signs its own input).

### POST /mint/broadcast
Body: `{session_id, signed_psbt_hex}` -> `{reveal_txid}`

### GET /mint/status/{session_id}
Returns: `{status, reveal_txid, counter_number, asset}`

## Read

- `GET /status` — server + active network.
- `GET /counters` — indexed counters (supports query params; see spec).
- `GET /counter/{id}` — one counter by id/asset (404 if unknown).

## AI assist (Gemini; 503 if GEMINI_API_KEY unset)

- `GET /ai/fee-advice` — mempool tiers + AI fee recommendation + estimated cost.
- `POST /ai/mint-parse` `{prompt}` — natural language -> `{asset, supply, divisible}`.
- `POST /ai/name-suggest` — content -> up to 3 Counterparty-valid asset names.

## Meta

- `GET /openapi.json` — OpenAPI 3.0 document.
- `GET /docs` — Swagger UI.

## Notes

- Signing requires a browser wallet (Unisat/Xverse/OKX/Horizon). A headless
  client can prepare/poll but not produce the signature.
- Use `network` + `explorer_base` from the prepare response for correct
  explorer links per network.
