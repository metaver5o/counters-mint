# ADR-0002: PSBT commit/reveal signing split

- Status: accepted
- Date: 2026-08-26
- Deciders: marco

## Context

An ordinal inscription uses the commit/reveal pattern: content is committed to a
taproot script-path output (commit tx), then spent to expose it (reveal tx). The
reveal must be signed with the ephemeral key that controls the inscription
script, but the user's funding input must be signed by their wallet. Private
keys must never leave the wallet, and the server must never hold user keys.

## Options considered

### Option A - Server pre-signs the reveal script input; wallet signs the funding input
Server builds both txs, signs the reveal's script-path input with the ephemeral
key it generated for this session, and hands the wallet a PSBT to sign only the
funding input. Server finalizes + broadcasts.
- Pros: user keys stay in the wallet; server only ever holds the throwaway
  inscription key; clean separation of responsibilities.
- Cons: server holds session state (ephemeral key + partially-signed tx) until
  the user completes; needs a session store with expiry.

### Option B - Wallet signs everything
Wallet holds/derives the inscription key too and signs both inputs.
- Pros: server holds no key material.
- Cons: wallets don't expose script-path taproot signing for arbitrary
  inscription scripts; not portable across Unisat/Xverse/OKX. Effectively
  infeasible today.

### Option C - Server holds user funds in a hot wallet
- Pros: simplest flow.
- Cons: custody of user funds — unacceptable.

## Decision

Option A. The server generates a per-session ephemeral key for the inscription
script, pre-signs the reveal's script-path input, and the wallet signs only its
funding input via PSBT. This mirrors the proven counters-mint flow.

## Consequences

- Non-custodial: user keys never leave the wallet; the only server-side key is a
  single-use inscription key with no value after reveal.
- Requires a session store (ephemeral key, commit/reveal state) with TTL and
  cleanup.
- Finalization must handle each wallet's returned signature form (key-path
  schnorr vs partial sig); this is the main source of wallet-specific bugs and
  needs regression tests.
- Tradeoff accepted: server statefulness during an in-flight mint, in exchange
  for non-custodial signing that works across all three wallets.
