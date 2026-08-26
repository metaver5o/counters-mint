# Architecture Decision Records

Decision log for counters-mint (the reference implementation of the skrybit
minting suite). Each record captures a decision, the context, the options
weighed, and the tradeoffs — so the *why* survives.

Format: [MADR](https://adr.github.io/madr/)-style. Status is one of
`proposed` / `accepted` / `superseded by ADR-XXXX`.

New decision: copy `0000-template.md` to the next number, fill it in, and add a
row here. Link the ADR from the PR that implements it.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-network-switch.md) | Single BTC_NETWORK switch (mainnet/testnet4/signet) | accepted |
| [0002](0002-psbt-commit-reveal.md) | PSBT commit/reveal signing split | accepted |
| [0003](0003-five-reviewer-ci.md) | Five automated PR reviewers plus CI | accepted |
