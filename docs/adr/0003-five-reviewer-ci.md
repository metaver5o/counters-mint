# ADR-0003: Five automated PR reviewers plus CI

- Status: accepted
- Date: 2026-08-26
- Deciders: marco

## Context

We want strong, low-effort review coverage on every PR without gating merges on
any single flaky/paid service. Candidates: Claude, CodeRabbit, Devin, Sentry,
SonarCloud — plus a CI gate (build, tests, lint).

## Options considered

### Option A - Run all five as non-blocking reviewers; CI is the only hard gate
Claude review + Sonar via GitHub Actions (kept `continue-on-error` so
credits/quota never block), CodeRabbit/Devin/Sentry via GitHub Apps, and a CI
workflow (frontend build, pytest, ruff) as the required check.
- Pros: broad, diverse review signal; no single vendor can block merges; CI
  stays authoritative and deterministic.
- Cons: comment noise; overlapping findings; per-tool config to maintain; some
  tools need paid credits to be useful (Devin).

### Option B - One reviewer only
- Pros: simplest, least noise.
- Cons: narrower coverage; single point of failure.

## Decision

Option A. Five reviewers, all advisory; CI (`ci.yml`) is the only hard gate.
CodeRabbit config lives in `.coderabbit.yaml`; Claude/Sonar in workflows; Devin/
Sentry are App installs. Documented in the README "Code review" section.

## Consequences

- Every PR gets multi-model review; merges depend only on deterministic CI.
- Ruff must stay green — a pre-existing dead-code break was cleared so it can gate.
- Known limits: Devin needs credits (trial expired); Sentry is AI-review-only;
  CodeRabbit may push auto-fix commits that re-trigger CI.
- Same setup is the template for ordinals-mint and tokens-mint.
