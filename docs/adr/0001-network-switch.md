# ADR-0001: Single BTC_NETWORK switch for mainnet / testnet4 / signet

- Status: accepted
- Date: 2026-08-26
- Deciders: marco

## Context

The app must run against mainnet, testnet4, and signet. Each changes the bech32
HRP (`bc` vs `tb`), the block explorer, and the RPC / Counterparty endpoints. An
early bug built a mainnet `bc1...` commit address while pointed at a `tb` chain —
because address HRP was not tied to the active network.

## Options considered

### Option A - One BTC_NETWORK var; endpoints resolve <NETWORK>_<NAME> then <NAME>
`_net_env()` resolves each endpoint in priority order so both networks can be
configured side by side and switched with one variable; HRP + explorer derive
from the same switch.
- Pros: single source of truth; both networks configurable at once; flipping one
  var repoints everything; hard to get address HRP out of sync.
- Cons: a bit of resolver indirection; env surface grows with prefixed names.

### Option B - Separate config file/profile per network
- Pros: explicit.
- Cons: duplication; drift between profiles; easy to run the wrong one.

## Decision

Option A. `BTC_NETWORK` selects the chain; `_net_env()` resolves
`<NETWORK>_<NAME>` first, then the plain `<NAME>`, then a built-in default. HRP
and explorer base come from the same switch (`config.hrp`, `config.explorer_base`).

## Consequences

- Address building, UI labels, and explorer links are network-correct by
  construction.
- Adding a network = add its prefixed env vars + HRP/explorer map entries.
- Signet currently has no Counterparty endpoint configured; minting there needs
  `SIGNET_CP_API_URL` set first.
- Adopted as the pattern for ordinals-mint and tokens-mint.
