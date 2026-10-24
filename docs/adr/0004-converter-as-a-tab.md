# 4. The converter is a tab of ganit, not its own tool

**Status:** Accepted  
**Date:** 2026-10-24

## Context

Converting money meant remembering qalc's syntax (`100 USD to INR`) and typing one expression per currency. A converter wants a different shape: an amount once, then every currency (or unit) you care about at the same time, with each rate and how old the rates are. It could be its own Vyom tool or part of ganit.

## Decision

Convert is a second tab of ganit (Vyom's tabs: `Ctrl+H` / `Ctrl+L`), opened directly with `vyom ganit convert`. Both tabs share qalc, the exchange rates and their refresh, the history and the number formatting. Calculate keeps qalc's full syntax; Convert parses only "amount + currency or unit" and asks qalc for every target in one run (expressions on stdin).

## Consequences

- One place for numbers: `Super+C` then `Ctrl+L`, and a key of its own if wanted (`vyom ganit convert`).
- Pinned currencies, the home currency and the digit grouping are ganit options (`currencies`, `home`, `grouping`).
- Convert's units are a fixed table of common ones per dimension; anything more unusual stays in Calculate (`3 parsec to ly`).
