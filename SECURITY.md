# Security Policy

## Scope

Undertow is a research project. The repository contains:

- a Python data pipeline (`engine/`) that reads **public** market data — no secrets,
  no API keys, no credentials;
- a static frontend (`web/`).

There is **no deployed smart contract** and **no production service** at this time, so
the on-chain attack surface is not yet applicable.

## Reporting a vulnerability

If you find a security issue (for example, a way the data pipeline could be made to
execute untrusted input, or a frontend XSS), please open a private report via GitHub
Security Advisories, or open an issue **without** sensitive details and ask a maintainer
to follow up privately.

Please do **not** open public issues that include exploit details for anything that
could harm users.

## Out of scope

- Market-data accuracy or model correctness (this is research; see the disclaimers in
  the README and whitepaper).
- Third-party data providers (e.g. the upstream market-data API).
