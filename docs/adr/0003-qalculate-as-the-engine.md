# 3. Use qalc (libqalculate) as the engine

**Status:** Accepted  
**Date:** 2026-10-19

## Context

A calculator people use daily needs units, currencies, percentages, dates and bases, and must not evaluate arbitrary code. Python's `eval` is unsafe and incomplete; writing a parser is a project of its own.

## Decision

Every expression goes to `qalc` with a timeout, and its answer is shown as you type. Exchange rates are refreshed once a day.

## Consequences

- Natural input works (`5 ft 11 in to cm`, `18% of 3897`).
- qalc is a required dependency.
