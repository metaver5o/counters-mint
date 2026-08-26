# Testnet4 mint verification checklist [SKRYBITDEV-669]

End-to-end verification of the browser-wallet mint flow on **testnet4** (and
signet), per wallet. This is a manual runbook: it needs a funded wallet, a
testnet4 bitcoind with `txindex`, and a Counterparty node — things CI cannot
provide. Run it before promoting `staging` -> `main` for a release.

## Prerequisites

- [ ] `bitcoind` on **testnet4** with `txindex=1`, RPC reachable.
- [ ] Counterparty Core reachable; `TESTNET4_CP_API_URL` set. (Signet has no CP
      node yet — set `SIGNET_CP_API_URL` first or signet mints have no CP backend.)
- [ ] Server started with `BTC_NETWORK=testnet4` (`docker compose up -d`).
- [ ] `GET /status` shows the expected network; `GET /openapi.json` loads; `/docs`
      renders.
- [ ] A wallet funded with testnet4 coins, holding at least one UTXO >=
      `min_source_sats` (see the prepare response) plus dust for the commit.

## Per-wallet matrix

Run the full flow (connect -> prepare -> commit send -> reveal -> sign -> broadcast
-> status) for each wallet.

**Acceptance criterion, scoped by network + build:**
- On **testnet4** (Counterparty backend present via `TESTNET4_CP_API_URL`): each
  wallet supported by the build must reach a **confirmed counter number**.
- On **signet**: require a confirmed counter number **only if** `SIGNET_CP_API_URL`
  is configured; otherwise verify broadcast + explorer, and treat CP indexing as
  N/A (no signet CP backend).
- Only run the OKX / Xverse rows on a build that includes #665 (below).

> **Prerequisite:** OKX and network-aware Xverse land with **SKRYBITDEV-665**
> (PR #9). On a build without #665, only **Unisat** and **Horizon** complete a
> full mint; **Xverse** signs but its commit-funding is a follow-up, and **OKX**
> is absent. Run the OKX/Xverse rows only on a build that includes #665 (which
> also makes Xverse request `tb1...` addresses on testnet4/signet and selects
> OKX's `bitcoinTestnet`/`bitcoinSignet` provider).

| Step | Unisat | Xverse | OKX | Horizon |
| --- | --- | --- | --- | --- |
| Detected + connects on testnet4 | [ ] | [ ] | [ ] | [ ] |
| Address HRP is `tb1...` (not `bc1`) | [ ] | [ ] | [ ] | [ ] |
| Commit send (dust -> commit addr) | [ ] | [ ] | [ ] | [ ] |
| Source UTXO selected (>= min) | [ ] | [ ] | [ ] | [ ] |
| Reveal PSBT signed (vin[0]) | [ ] | [ ] | [ ] | [ ] |
| Broadcast accepted | [ ] | [ ] | [ ] | [ ] |
| Explorer link points to testnet4 | [ ] | [ ] | [ ] | [ ] |

Wallet-specific notes:
- **Unisat / OKX / Horizon** — share the `signPsbt(hex)` provider API; OKX must
  use its network-specific provider (`bitcoinTestnet`).
- **Xverse** — signs via sats-connect (`signPsbt`, base64). Its commit-funding
  path differs (`sendTransfer`, no `getUtxos`); confirm the commit send and
  source-UTXO steps specifically. See SKRYBITDEV-665.

## Counterparty indexing

- [ ] After broadcast, the reveal tx confirms.
- [ ] Counterparty indexes the issuance; `GET /mint/status/<sid>` resolves a
      `counter_number` (not just `broadcast`).
- [ ] `GET /counter/<asset>` returns the new counter.

## Network switch sanity

- [ ] Flip `BTC_NETWORK=signet`, restart: HRP still `tb`, explorer ->
      `mempool.space/signet`, endpoints repoint (config `_net_env`).
- [ ] Flip back to `mainnet`: HRP `bc`, explorer root, `bc1p` commit address.

## Mainnet readiness (before going live)

- [ ] Mainnet bitcoind (`txindex`) + Counterparty node configured
      (`CP_API_URL` / `BTC_RPC_URL` or their `MAINNET_` prefixes).
- [ ] Fee policy reviewed (`REVEAL_VSIZE_ESTIMATE`, `MIN_RELAY_FEE`); economy tier
      still above min-relay at current mempool.
- [ ] Dust / min-source thresholds validated against a real mainnet UTXO.
- [ ] At least one small real mainnet mint completed and indexed.
- [ ] Rollback plan: sessions are in-memory; a restart drops in-flight mints
      (users re-prepare) — acceptable, documented.

## Recording results

Note the tx ids + counter numbers per wallet in the ticket (SKRYBITDEV-669) when
the run passes, so the release has an auditable verification trail.
