# TestGhost — Reference & Vision Document

**Read this file before creating anything new in this project.** It defines what
TestGhost is for, what already exists, what is intentionally off-limits to change,
and what the next real feature is. This file works alongside two other reference
documents already in this repo:

- `TestGhost_Completion_And_Uniqueness.md` — the completion checklist (Part 1) and
  the list of intentional design decisions that must not be "fixed" (Part 2)
- `TestGhost_Execution_Pack.md` — the original day-by-day build plan and prompt
  sequence used to construct the codebase

This document does not repeat either of those — it adds two things they don't
cover: **why someone would actually keep using TestGhost**, and **the next real
feature to build once the existing pipeline is verified working.**

---

## 1. The one-sentence answer to "why would anyone visit this"

> **TestGhost isn't a one-time test generator — it's a memory of your API's
> behavior over time, so it can tell you exactly what silently changed between
> two points in your app's history, not from a changelog, but from real captured
> traffic.**

Every comparable tool (Tusk Drift, VCR, Diffblue, Postman's test generation)
generates tests once and stops there. TestGhost already computes a vector
embedding for every captured endpoint, for deduplication purposes, within a
single session. **That same embedding store, reused across sessions instead of
discarded after one, is what makes TestGhost worth coming back to** — not just
once to bootstrap a test suite, but every time before a deploy, to catch drift
a human reviewer would never notice by reading a diff.

This is the feature described in Section 3 below. It does not require new
infrastructure — it reuses the existing `embeddings` table and `pgvector`
cosine-similarity mechanism already built for Stage 2 deduplication.

---

## 2. Current state — do not assume completion

As of the last verified check, the core 6-layer pipeline is implemented in code
but **has not been confirmed to run end to end**. Specific known issues at last
check: dependency installation inconsistencies between environments, a database
port mismatch, and `pytest` collecting 0 test items (meaning no real generated
test files existed yet at verification time).

**Before any new feature work begins, `TestGhost_Completion_And_Uniqueness.md`
Part 1 must show a real PASS on every item**, verified by actual command output,
not by a file existing with the right name. Do not report the project as
"production-ready" or "complete" without this verification. See Section 4 for
how this applies to the loop-based working process.

---

## 3. The next feature — Session Drift Detection

### What it does

Given two session IDs — typically "before a change" and "after a change" —
TestGhost compares the captured endpoints between them using the **already
computed embeddings**, and reports:

- **New endpoints** — present in the second session, not the first
- **Removed endpoints** — present in the first session, not the second
- **Changed endpoints** — same semantic endpoint (high embedding similarity,
  matched the same way deduplication already works), but the response shape
  has measurably changed: different top-level JSON keys, a status code that
  wasn't observed before, or a response time that moved outside the previously
  observed range
- **Untested gaps** — an endpoint that has existed across every session but has
  never once been captured returning a non-200 status code

### Why this fits the existing architecture, not against it

This feature does not introduce new ML models or change any existing pipeline
stage. It is a **read-only query layer** on top of data that already exists:

- Reuses the `embeddings` table exactly as Stage 2 (deduplication) already does,
  just comparing across two `session_id` values instead of within one
- Reuses the same cosine-similarity mechanism from `ml/deduplicator.py` — a
  "changed endpoint" is simply two embeddings with the **same normalized path**
  but a meaningfully different response-body schema fingerprint between the two
  sessions
- Does not touch the LangGraph agent, the anomaly detector, or the clusterer —
  this is a new CLI command and a new read-only API endpoint, not a new pipeline
  stage

### Proposed interface

```
testghost diff <session_id_before> <session_id_after>
```

Outputs a terminal summary (new/removed/changed/untested-gap counts) and writes
an HTML diff report to `output/reports/diff_<before>_<after>.html`, styled
consistently with the existing session report.

### New files this would require (does not modify existing pipeline files)

```
ml/drift_detector.py          # Compares two sessions' embeddings + response schemas
backend/routers/diff.py       # GET /diff?before=<id>&after=<id>
reporting/diff_reporter.py    # Renders the diff HTML report
reporting/templates/diff.html # New template, separate from report.html
```

### Explicit scope boundary

This feature compares **two already-completed sessions**. It does not attempt
live/continuous monitoring, does not run in CI automatically, and does not
require any new environment variables beyond what already exists. Keep it this
scoped — this is intentionally the smallest version of the idea that still
delivers the "why visit" value proposition. Expanding it into a CI-integrated
regression gate is legitimate v3 scope, not part of this task.

---

## 4. The working process — loop, don't leap

For any task touching this project, work in this exact loop, per item, not in
one large pass:

```
PLAN → ACT → VERIFY → (if FAIL: diagnose → fix → VERIFY again) → only then NEXT ITEM
```

Never mark an item complete because an action was taken — only because the
verification step produced real, checkable evidence that it worked. This applies
to both fixing existing issues (checklist items in
`TestGhost_Completion_And_Uniqueness.md`) and to building the new drift-detection
feature once the baseline is proven.

---

## 5. Hard constraints carried over from the Uniqueness document

Do not violate any of the 8 items in Part 2 of `TestGhost_Completion_And_Uniqueness.md`
while implementing anything in this document, including the drift detection
feature. In particular: drift detection must use the existing embedding-based
similarity approach, not introduce an LLM call to "decide" whether something
changed — that would contradict the project's deliberate use of classical,
explainable methods where they are the correct tool.
