# Bitcoin Counters — Mint

Mint a **Bitcoin Counter**: a file stored in Bitcoin witness data, owned through a
Counterparty asset, numbered from zero. Connect a wallet, drop a file, and inscribe.

This is the standalone **minting app** — the interactive counterpart to the read-only
explorer at [proto.bitcoincounters.com](https://proto.bitcoincounters.com). It ships the
full inscription engine plus a focused Svelte 5 front end, sharing the original Bitcoin
Counters branding (copper / IBM Plex mono).

## Features

- **Wallet minting** — Unisat and Horizon (Ordinalsafe) via PSBT; Xverse detection (signing soon).
- **AI assist** — natural-language mint parsing, asset-name suggestions, and a fee advisor
  (`/ai/*` routes, powered by Gemini).
- **Full backend engine** — taproot envelope builder, Counterparty asset issuance, Bitcoin
  Core RPC wiring, wallet derivation (BIP39 / Electrum v1 / v2). Keys stay in Bitcoin Core.

## Stack

- **Frontend** — `web/` — Svelte 5 + TypeScript + Vite. Builds into `counters_proto/server/static/`.
- **Backend** — `counters_proto/` — pure-Python HTTP server + CLI (`counters-proto`), no heavy deps.

## Quick start (Docker)

```bash
cp .env.example .env      # fill in BTC_RPC_*, CP_API_URL, ANTHROPIC/GEMINI key
docker build -t counters-mint .
docker run --rm -p 8082:8082 --env-file .env -v "$PWD/data:/data" counters-mint
# open http://localhost:8082
```

## Local development

```bash
# backend
pip install -e .
counters-proto server --host 0.0.0.0 --port 8082

# frontend (separate shell) — Vite dev server with HMR
cd web
npm install
npm run dev
```

`npm run build` compiles the front end into `counters_proto/server/static/`, which the
Python server serves directly in production.

## Configuration

See `.env.example`. Key settings: `BTC_RPC_URL` / `BTC_RPC_USER` / `BTC_RPC_PASSWORD`
(Bitcoin Core with `txindex`), `CP_API_URL` (Counterparty Core), and an AI API key for
the `/ai/*` routes.

## Tests

```bash
pip install -e '.[dev]'
pytest
```

## License

See upstream [BitcoinCounters/counters-proto](https://github.com/BitcoinCounters/counters-proto).
