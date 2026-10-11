# TestGhost — Completion Checklist & Uniqueness Specification



## Purpose of this document



This file has two jobs:



1. **Part 1** is a checklist of everything required for TestGhost to be considered fully

   complete and working end to end. Use it to audit current state against target state.

2. **Part 2** is a list of architectural decisions that are **intentional and unique** —

   things that may look unusual or "wrong" to a generic code review, but exist for

   specific reasons. Do not "fix," simplify, or revert anything in Part 2 without

   explicitly asking first and explaining why you think it should change.



**Instructions for Antigravity:** Treat this as an audit checklist, not a task list to

execute blindly. For Part 1, check each item against the actual codebase and report

PASS/FAIL/PARTIAL with evidence (a file, a command output, a test result) — do not mark

something complete just because a file with the right name exists. For Part 2, read it

before touching any related code, and treat it as a constraint, not a suggestion.



---



## PART 1 — Completion Checklist



### 1.1 Environment & Infrastructure



- [x] Python 3.12 virtual environment exists at `.venv` and is the one actually used

      (verify with `where python` while activated — must NOT resolve to Anaconda or

      any other global install)

- [x] `pip install -e .` completes with zero errors, and `pip list` inside the venv

      shows every package from `requirements.txt` present

- [x] Docker Desktop running, `docker compose up -d` brings up a healthy PostgreSQL +

      pgvector container

- [x] `.env` contains a real `ANTHROPIC_API_KEY` (or equivalent for whichever provider

      is configured) — not the placeholder value

- [x] `.env` `DATABASE_URL` and `DATABASE_URL_SYNC` match the actual port Docker is

      running on (verify against `docker compose ps` output, not assumed defaults)

- [x] `alembic upgrade head` runs clean; all 4 tables + `alembic_version` exist

- [x] pgvector extension is active inside the database

      (`SELECT * FROM pg_extension WHERE extname = 'vector';` returns a row)

- [x] mitmproxy CA certificate is installed and trusted in the Windows Current User

      root store (`certutil -user -store root | findstr mitmproxy` returns a match)

- [ ] A browser proxy toggle (FoxyProxy or equivalent) is configured for

      `127.0.0.1:8080`



### 1.2 Backend — starts and connects correctly



- [x] `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` starts with

      **no traceback**, including no database connection errors during the lifespan

      startup event

- [ ] `GET /health` returns `{"status": "ok", "version": "0.2.0"}`

- [ ] `POST /session/start` returns a real UUID `session_id`

- [ ] `POST /session/stop` correctly marks a session complete and returns an accurate

      `request_count`

- [ ] `GET /session/list` returns previously created sessions with correct stats



### 1.3 Proxy capture — the core innovation, must work end to end



- [ ] `testghost start --session "<name>"` launches both the backend subprocess and

      mitmproxy without error, and prints a real session ID

- [ ] Browsing an HTTPS site through the proxy (with FoxyProxy on) results in **at

      least one row** appearing in `captured_requests` after `testghost stop`

      (verified by direct SQL query, not just trusting CLI output)

- [ ] Request and response bodies in the database are **not empty** for a real

      HTTPS request (empty bodies = certificate not actually trusted, even if

      `certutil` shows it installed)

- [ ] PII scrubbing is verified manually at least once: a request containing a

      real email/token/card-like string is captured and confirmed scrubbed

      (`[SCRUBBED_EMAIL]` etc. appears in the stored body, not the real value)



### 1.4 ML pipeline — each layer functional, not just present as a file



- [ ] `ml/embedder.py` produces a 384-dimension vector for a real captured request

- [ ] Running the same endpoint twice in one session results in the second capture

      being flagged `is_duplicate = true` in the database

- [ ] A genuinely different endpoint is **not** incorrectly flagged as a duplicate

- [ ] After 50+ real captured requests, `python -m ml.train_anomaly_model` completes

      and writes `models/isolation_forest.pkl`

- [ ] Once trained, a deliberately slow/oversized test response is correctly flagged

      `is_anomaly = true`

- [ ] With 6+ unique captured endpoints in a session, `cluster_session()` assigns

      more than one `cluster_label` (not everything dumped into "general")



### 1.5 LangGraph agent — generates real, usable code



- [ ] `testghost generate --session <id>` completes without hanging or timing out

- [ ] The 4 nodes (classifier, planner, writer, validator) are each observably

      invoked — confirmed via logs, not assumed

- [ ] Generated code passes `ast.parse()` (syntactically valid Python)

- [ ] Generated code, when manually reviewed, contains assertions that match the

      **real** captured request/response — not generic placeholder assertions

- [ ] The retry path is confirmed to work at least once: deliberately trigger a

      validation failure and confirm the writer node is called again with feedback



### 1.6 Evaluation layer — actually gates quality, not just present



- [ ] `evaluation/grader.py` produces a score between 0 and 1 for a real generated test

- [ ] A deliberately bad test (no assertions) scores below the 0.70 threshold

- [ ] A deliberately good test scores above the threshold

- [ ] The retry controller is confirmed to trigger regeneration for a low-scoring test

      at least once in a real run, not just in isolated unit tests



### 1.7 Output — files and report are real and correct



- [ ] `output/tests/test_<cluster>.py` files exist after a real `generate` run

- [ ] `output/tests/conftest.py` exists with a working `base_url` fixture

- [ ] `pytest output/tests/ -v` **collects more than 0 items** and actually runs

      (this was previously failing — must be re-verified after every environment fix)

- [ ] `output/reports/report_<session_id>.html` opens in a browser and shows real

      data — not an empty template



### 1.8 CLI — full command set works



- [ ] `testghost --help` lists all commands

- [ ] `testghost start`, `stop`, `generate`, `sessions` all function as documented

- [ ] Running these commands from a fresh terminal (after closing and reopening)

      still works — proves state isn't dependent on a single terminal session



### 1.9 Documentation



- [ ] `README.md` exists, contains no secrets, no real file paths with a username,

      no real ports/IPs beyond documented defaults

- [ ] Setup instructions in the README have been personally followed start to finish

      at least once and confirmed accurate



### 1.10 Not required for MVP — explicitly out of scope for now



These are legitimate v2 items. Do not attempt them unless asked directly:



- [ ] Jest/JavaScript test generation (pytest only for now)

- [ ] GitHub Actions CI

- [ ] PyPI publishing

- [ ] Docker Compose running the backend itself (Postgres-only compose is sufficient)

- [ ] Team/multi-user session sharing



---



## PART 2 — What Makes This Project Unique (do not "fix" these)



Each item below is a deliberate design decision. If something in this list looks like

a bug, inefficiency, or unconventional choice, it is very likely intentional — ask

before changing it.



### 2.1 Network-layer capture instead of an SDK



TestGhost uses `mitmproxy` to intercept traffic at the network layer rather than

requiring an SDK inside the target application's codebase (the way comparable tools

like Tusk Drift work). **This is the core differentiator of the entire project.**

It means TestGhost works on any application in any language, including third-party

APIs the user doesn't own. Do not suggest replacing this with an SDK-based approach —

that would eliminate the project's main reason for existing.



### 2.2 Classical ML instead of LLM calls for anomaly detection and clustering



Isolation Forest (anomaly detection) and KMeans (clustering) are used deliberately

instead of asking an LLM to make these judgments. This is not a cost-cutting shortcut —

it is a design statement that classical ML is the correct tool for statistical outlier

detection and unsupervised grouping, and that routing every decision through an LLM is

not automatically "more AI" or better engineering. Do not replace these with LLM calls.



### 2.3 Multi-node LangGraph agent instead of a single prompt



The Classifier → Planner → Writer → Validator pipeline could technically be collapsed

into one large prompt asking an LLM to "write good tests for this endpoint." This was

deliberately avoided. The multi-step, stateful approach produces more reliable output,

supports targeted retries (only the Writer re-runs on failure, not the whole pipeline),

and reflects how production agentic systems are actually built. Do not simplify this

into a single API call, even if it would reduce token usage.



### 2.4 A self-grading, auto-retry output loop



Generated tests are not saved directly — they pass through a DeepEval-based scoring

step first, with automatic regeneration for anything below threshold. This is

intentionally more expensive (more LLM calls) than a "generate once and hope" approach.

Do not remove or bypass this loop to save time or cost without being asked.



### 2.5 RAG-based deduplication using pgvector, not exact-match



Deduplication uses semantic similarity via embeddings, not a simple `path == path`

string match. This is deliberate — different-looking paths (`/users/123` vs

`/users/456`) need to be recognized as the same endpoint pattern, which exact matching

cannot do. Do not replace the embedding-based approach with a simpler string comparison

even if it looks like it would "simplify" the code.



### 2.6 PII scrubbing happens before persistence, not after



Sensitive data is scrubbed in the mitmproxy addon itself, before the payload ever

reaches the FastAPI backend or database. This is a deliberate security boundary — the

scrubbing must never be moved to happen after storage, even temporarily for debugging

purposes.



### 2.7 Graceful no-op behavior when data is insufficient



The anomaly detector and clusterer are designed to silently skip their function (not

crash, not error) when there isn't enough data yet — anomaly detection needs 50+

captured requests, clustering needs 6+ unique endpoints. This is intentional graceful

degradation, not a bug. Do not add error-throwing behavior here; the correct behavior

is exactly what's already implemented.



### 2.8 Provider-agnostic LLM client design



The system is designed to swap between Anthropic, Gemini, Groq, or OpenRouter via a

single environment variable (`LLM_PROVIDER`), rather than being hardcoded to one

provider. This exists specifically so the project isn't dependent on a single paid

API. Preserve this abstraction if making any changes to how nodes call the LLM.



---



## How to use this document going forward



Re-run the Part 1 checklist after any significant change to confirm nothing regressed.

Treat any item that was previously PASS and is now FAIL as a priority bug, even if it

seems unrelated to whatever was just changed. Part 2 does not need to be re-verified

repeatedly — it only needs to be consulted before modifying anything touching those

specific areas.
