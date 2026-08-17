# TestGhost — Complete Execution Pack
> For use directly in Antigravity, Claude, ChatGPT, Cursor, Windsurf, or Codex.
> Every section is copy-paste ready. Nothing is generic.

---

## PART 1 — 10-DAY DAY-BY-DAY IMPLEMENTATION ORDER

---

### DAY 1 — Repo skeleton + environment

**Goal:** A working repo you can run, even if it does nothing yet.

**Tasks:**
- Create the full folder structure (see Part 4 for the tree)
- Set up `pyproject.toml` with all dependencies declared but not all installed
- Create `.env.example` with all required env vars listed
- Create `docker-compose.yml` with PostgreSQL + pgvector service only
- Write a bare `main.py` that starts FastAPI and returns `{"status": "ok"}` on GET /health
- Write a bare `cli.py` with `testghost start`, `testghost stop`, `testghost generate` as Click stubs that print "not implemented yet"
- Run `docker compose up -d` and confirm postgres starts
- Run `uvicorn backend.main:app --reload` and hit `/health`

**Completion check:**
- [ ] `curl localhost:8000/health` returns 200
- [ ] `testghost start` prints "not implemented" without crashing
- [ ] Docker postgres is up and accessible via psql

**Red flag:** If pyproject.toml installs fail or Docker postgres won't start — fix this before day 2. Everything depends on it.

---

### DAY 2 — Database schema + pgvector

**Goal:** All tables created, pgvector extension enabled, ORM models working.

**Tasks:**
- Enable pgvector extension in postgres via init SQL
- Write SQLAlchemy ORM models: `Session`, `CapturedRequest`, `Embedding`, `GeneratedTest`
- Write Alembic migration for all four tables
- Write `db/session.py` for database connection management
- Write `db/init_db.py` that creates all tables on startup
- Test: insert one fake `CapturedRequest` row manually and read it back

**Files generated today:**
- `backend/db/models.py`
- `backend/db/session.py`
- `backend/db/init_db.py`
- `alembic/versions/001_initial_schema.py`

**Completion check:**
- [ ] `alembic upgrade head` runs without error
- [ ] pgvector extension is active: `SELECT * FROM pg_extension WHERE extname = 'vector';`
- [ ] All four tables visible in psql
- [ ] One test insert + read works in a scratch script

**Red flag:** If SQLAlchemy Vector column type fails — you need `pgvector` Python package and the correct column declaration. Do not proceed until this is resolved.

---

### DAY 3 — FastAPI control plane + session management

**Goal:** The three core API endpoints working and persisting to the database.

**Tasks:**
- `POST /session/start` — creates a session row, returns session_id
- `POST /capture` — validates session is active, stores a CapturedRequest row
- `POST /session/stop` — marks session as complete
- `GET /sessions` — returns list of all sessions with request counts
- Write Pydantic request/response schemas for all four
- Write basic error handling: 404 if session not found, 409 if session already active

**Files generated today:**
- `backend/routers/sessions.py`
- `backend/routers/capture.py`
- `backend/schemas/session.py`
- `backend/schemas/capture.py`

**Completion check:**
- [ ] POST /session/start returns a UUID session_id
- [ ] POST /capture stores a row in captured_requests
- [ ] POST /session/stop marks it complete
- [ ] GET /sessions returns a list
- [ ] Posting to a stopped session returns 409

**Red flag:** If sessions are not persisting across requests — check that you are not using SQLite in memory by accident. The connection string must point to Postgres.

---

### DAY 4 — mitmproxy addon + PII scrubber

**Goal:** Browsing through the proxy captures real traffic and sends clean payloads to FastAPI.

**Tasks:**
- Write `proxy/addon.py` as a mitmproxy addon class
- Hook `request()` and `response()` events
- Build the payload dict: method, url, path, headers, request_body, response_status, response_body, response_time_ms
- Write `proxy/scrubber.py` with regex patterns for: email, phone, JWT, credit card, SSN, IP address
- After scrubbing, POST to `http://localhost:8000/capture` with the session_id from env or CLI arg
- Write a launch helper: `proxy/runner.py` that starts mitmdump with the addon

**Files generated today:**
- `proxy/addon.py`
- `proxy/scrubber.py`
- `proxy/runner.py`

**Completion check:**
- [ ] `mitmdump -p 8080 -s proxy/addon.py` starts without error
- [ ] Browser configured to proxy through 8080 — visit httpbin.org/get — request appears in captured_requests table
- [ ] A fake JWT in a request body is scrubbed before storage
- [ ] Response body over 50KB is truncated to 50KB before storage

**Red flag:** If mitmproxy cannot intercept HTTPS — the root CA cert is not installed in the browser. Run `mitmproxy` once manually, then install the cert from `~/.mitmproxy/mitmproxy-ca-cert.pem`. Do not skip this.

---

### DAY 5 — Embedding engine + RAG deduplication

**Goal:** Every captured request is embedded and checked for duplicates before test generation.

**Tasks:**
- Write `ml/embedder.py` — loads `all-MiniLM-L6-v2` from sentence-transformers, embeds a string representation of method + path + body_schema
- Write `ml/deduplicator.py` — cosine similarity query against pgvector embeddings table, returns True if similarity > 0.92
- Integrate both into the `/capture` endpoint: embed on arrival, check duplicates, store embedding if not duplicate
- Add `is_duplicate` and `duplicate_of_id` columns to captured_requests (add via Alembic migration)

**Files generated today:**
- `ml/embedder.py`
- `ml/deduplicator.py`
- `alembic/versions/002_add_duplicate_fields.py`

**Completion check:**
- [ ] First capture of `POST /api/users` stores an embedding
- [ ] Second capture of same endpoint is flagged as duplicate (is_duplicate=True)
- [ ] Different endpoint `GET /api/users/1` is NOT flagged as duplicate
- [ ] Embedding vector has 384 dimensions in the database

**Red flag:** If all requests are flagged as duplicates — your embedding string is too generic (just the method). Include path + body schema shape. If nothing is flagged — threshold may be too high. Test similarity scores manually before tuning threshold.

---

### DAY 6 — Isolation Forest anomaly detector

**Goal:** Unusual responses are automatically flagged and will get extra edge-case tests.

**Tasks:**
- Write `ml/feature_extractor.py` — extracts 6 features from a CapturedRequest: response_time_ms, response_body_size, status_code, json_field_count, json_nesting_depth, content_type_encoded_as_int
- Write `ml/anomaly_detector.py` — loads or trains IsolationForest, scores a feature vector, returns True if score < -0.1
- Write `ml/train_anomaly_model.py` — trains on first 200 normal requests, saves as `models/isolation_forest.pkl` using joblib
- Integrate scoring into `/capture` endpoint: score each response, store `anomaly_score` and `is_anomaly` in captured_requests
- Add these columns via Alembic migration

**Files generated today:**
- `ml/feature_extractor.py`
- `ml/anomaly_detector.py`
- `ml/train_anomaly_model.py`
- `models/` directory (gitignored except `.gitkeep`)
- `alembic/versions/003_add_anomaly_fields.py`

**Completion check:**
- [ ] 100 synthetic normal responses stored — model trains successfully
- [ ] A manually crafted response with 50KB body and 5000ms response time scores as anomaly
- [ ] A normal 200ms, 1KB JSON response scores as normal
- [ ] `models/isolation_forest.pkl` file exists after training

**Red flag:** If every response is anomalous — your training data is too small or too varied. Use at least 100 synthetic normal examples. If nothing is ever anomalous — contamination parameter in IsolationForest may be too low. Default is 0.1, start there.

---

### DAY 7 — KMeans endpoint clustering

**Goal:** After a session, endpoints are grouped semantically so test files have logical structure.

**Tasks:**
- Write `ml/clusterer.py` — loads all embeddings for a session, runs KMeans with k selected by silhouette score (k=2 to k=8)
- Assign cluster label to each captured_request (add `cluster_id` and `cluster_label` columns)
- Write label heuristic: most common path prefix in cluster becomes the label (auth, users, admin, public, etc.)
- Store cluster assignments in captured_requests

**Files generated today:**
- `ml/clusterer.py`
- `alembic/versions/004_add_cluster_fields.py`

**Completion check:**
- [ ] Session with 20 diverse endpoints clusters into 3-5 groups
- [ ] All endpoints with `/api/auth/` prefix land in the same cluster
- [ ] Cluster labels are human-readable strings, not just integers
- [ ] Silhouette score is logged so you can inspect cluster quality

**Red flag:** If all endpoints land in one cluster — your embeddings are too similar (method+path only). Add response schema shape to the embedding string. If clusters are random with no pattern — increase minimum session size before clustering runs (at least 10 unique endpoints).

---

### DAY 8 — LangGraph 4-node agent

**Goal:** The core AI generation pipeline — a stateful 4-node graph that produces correct test code.

**Tasks:**
- Define `AgentState` TypedDict in `langgraph_pipeline/state.py`
- Write `langgraph_pipeline/nodes/classifier.py` — reads request+response, outputs endpoint_type and risk_level
- Write `langgraph_pipeline/nodes/planner.py` — outputs list of test scenarios based on endpoint_type
- Write `langgraph_pipeline/nodes/writer.py` — generates pytest code with parametrize decorators
- Write `langgraph_pipeline/nodes/validator.py` — runs `ast.parse()` on output, retries if broken (max 2 retries)
- Wire the graph in `langgraph_pipeline/graph.py` — edges: classifier → planner → writer → validator, retry edge from validator back to writer
- Write `langgraph_pipeline/prompts.py` — all system and user prompt templates as Python string constants (not inline in nodes)

**Files generated today:**
- `langgraph_pipeline/state.py`
- `langgraph_pipeline/nodes/classifier.py`
- `langgraph_pipeline/nodes/planner.py`
- `langgraph_pipeline/nodes/writer.py`
- `langgraph_pipeline/nodes/validator.py`
- `langgraph_pipeline/graph.py`
- `langgraph_pipeline/prompts.py`

**Completion check:**
- [ ] Graph runs end-to-end on one captured request without crashing
- [ ] Classifier correctly identifies `POST /api/login` as auth type
- [ ] Planner outputs at least 3 test scenarios for a CRUD endpoint
- [ ] Writer output is valid Python (ast.parse passes)
- [ ] Validator retries when writer produces invalid syntax
- [ ] All 4 node calls are visible in logs with their inputs and outputs

**Red flag:** If the Writer node produces valid-looking but logically wrong tests (asserting wrong status codes, missing assertions) — your prompt is not specific enough. The Writer prompt MUST include: the actual request body, the actual response body, the actual status code, and explicit instructions to assert all three. Do not use a vague "write a test" prompt.

---

### DAY 9 — DeepEval scoring + retry loop + test file output

**Goal:** Every generated test is graded. Low-quality tests are regenerated. Files are saved.

**Tasks:**
- Write `evaluation/grader.py` — implements 3 DeepEval metrics: CoverageMetric, CorrectnessMetric, EdgeCoverageMetric
- Write `evaluation/retry_controller.py` — if overall score < 0.70, sends test back to writer node with feedback, max 2 retries
- Write `generation/file_writer.py` — writes pytest files to `output/tests/test_{cluster_label}.py`, one per cluster
- Write `generation/conftest_writer.py` — generates `conftest.py` with shared fixtures per cluster
- Store generated test metadata in `generated_tests` table: score, retry_count, cluster_id, session_id, file_path

**Files generated today:**
- `evaluation/grader.py`
- `evaluation/retry_controller.py`
- `generation/file_writer.py`
- `generation/conftest_writer.py`

**Completion check:**
- [ ] A deliberately bad test (no assertions) scores below 0.70 and triggers regeneration
- [ ] A good test scores above 0.70 and is saved without retry
- [ ] `output/tests/test_auth.py` file exists and is valid Python after generation
- [ ] `output/tests/conftest.py` exists with at least one fixture
- [ ] `generated_tests` table has rows with scores and file paths

**Red flag:** If DeepEval scores everything 0.0 — check that your test cases are being constructed correctly as DeepEval `LLMTestCase` objects. The actual_output must be the generated test code as a string. If scores are all 1.0 — your metrics may be too lenient. Print the reasoning output of each metric and inspect it manually.

---

### DAY 10 — HTML report + CLI wiring + end-to-end run

**Goal:** Full end-to-end flow works from `testghost start` to `testghost generate` to `open report.html`.

**Tasks:**
- Write `reporting/reporter.py` — Jinja2 template rendering the HTML report
- Report sections: summary stats, cluster table, per-test confidence scores, anomaly-flagged tests highlighted, duplicate coverage count
- Write `output/report_template.html` as Jinja2 template
- Wire CLI: `testghost start` launches proxy/runner.py + FastAPI via subprocess
- Wire CLI: `testghost stop` calls POST /session/stop
- Wire CLI: `testghost generate` calls POST /generate which triggers clusterer → LangGraph → grader → file_writer → reporter in sequence
- Add `POST /generate` endpoint to FastAPI that orchestrates the full pipeline

**Files generated today:**
- `reporting/reporter.py`
- `reporting/templates/report.html`
- Final wiring in `backend/routers/generate.py`
- Final wiring in `cli/cli.py`

**Completion check:**
- [ ] `testghost start --session "test-run-1"` starts everything
- [ ] Browsing httpbin.org through proxy captures requests
- [ ] `testghost stop` stops the session
- [ ] `testghost generate` produces test files AND an HTML report
- [ ] `open output/report.html` shows a real report with real data
- [ ] The full flow takes under 60 seconds from stop to report

**Red flag:** If the generate command hangs — the LangGraph pipeline or DeepEval is waiting indefinitely. Add a 30-second timeout to every LLM call. If the HTML report is blank — check that Jinja2 is receiving a populated data dict. Print the dict before rendering.

---

## PART 2 — PROMPT-BY-PROMPT ANTIGRAVITY BUILD SEQUENCE

Use these prompts in order. Each is scoped to one file batch. Never combine two batches into one prompt.

---

### PROMPT 1 — Repo scaffold

```
You are building a Python project called TestGhost.

Create the complete folder structure with empty placeholder files.
The project has these top-level directories:
proxy/, backend/, ml/, langgraph_pipeline/, evaluation/, generation/, reporting/, cli/, output/, models/, tests/, alembic/

Under backend/: main.py, db/, routers/, schemas/
Under backend/db/: models.py, session.py, init_db.py
Under backend/routers/: sessions.py, capture.py, generate.py
Under backend/schemas/: session.py, capture.py
Under ml/: embedder.py, deduplicator.py, feature_extractor.py, anomaly_detector.py, train_anomaly_model.py, clusterer.py
Under langgraph_pipeline/: state.py, graph.py, prompts.py, nodes/classifier.py, nodes/planner.py, nodes/writer.py, nodes/validator.py
Under evaluation/: grader.py, retry_controller.py
Under generation/: file_writer.py, conftest_writer.py
Under reporting/: reporter.py, templates/report.html
Under cli/: cli.py
Under tests/: test_capture.py, test_embedder.py, test_anomaly.py, test_langgraph.py

Also create:
- pyproject.toml with all dependencies
- .env.example with all required environment variables
- docker-compose.yml with postgres+pgvector service
- README.md with one-paragraph project description

Output each file path as a header followed by its content.
For placeholder files, add a one-line comment describing the file's purpose.
Do not implement any logic yet. Scaffold only.
```

---

### PROMPT 2 — Database models + Alembic

```
You are implementing the database layer for TestGhost, a Python project.

Write the following files completely:

FILE: backend/db/models.py
- SQLAlchemy ORM models using DeclarativeBase
- Model: Session (id UUID, name str, status enum active/complete, created_at, ended_at)
- Model: CapturedRequest (id UUID, session_id FK, method str, path str, url str, request_headers JSON, request_body Text, response_status int, response_body Text, response_time_ms float, is_duplicate bool default False, duplicate_of_id UUID nullable, anomaly_score float nullable, is_anomaly bool default False, cluster_id int nullable, cluster_label str nullable, created_at)
- Model: Embedding (id UUID, captured_request_id FK unique, vector Vector(384), created_at)
- Model: GeneratedTest (id UUID, session_id FK, cluster_label str, file_path str, code Text, eval_score float, retry_count int default 0, is_high_confidence bool default False, created_at)
- Import Vector from pgvector.sqlalchemy

FILE: backend/db/session.py
- Async SQLAlchemy engine using asyncpg
- DATABASE_URL from environment variable
- get_db() async generator for FastAPI dependency injection

FILE: backend/db/init_db.py
- async init_db() function that creates all tables if not exist
- Called on FastAPI startup

FILE: alembic/env.py
- Configured for async SQLAlchemy
- Imports all models so autogenerate works

Also write the first Alembic migration file that creates all four tables.
Include the pgvector extension creation in the migration.
Use realistic column types. No shortcuts.
Output each file separately with the file path as a header.
```

---

### PROMPT 3 — FastAPI routers

```
You are implementing the FastAPI control plane for TestGhost.

Write these files completely:

FILE: backend/main.py
- FastAPI app with lifespan that calls init_db() on startup
- Include routers: sessions, capture, generate
- CORS middleware allowing localhost
- GET /health returning {"status": "ok", "version": "0.1.0"}

FILE: backend/routers/sessions.py
- POST /session/start: body has optional name field, creates Session row, returns session_id and name
- POST /session/stop: body has session_id, marks session complete, returns request_count
- GET /sessions: returns list of all sessions with id, name, status, request_count, created_at

FILE: backend/routers/capture.py
- POST /capture: body is CapturePayload schema
- Validates session exists and is active, returns 404 if not
- Returns 409 if session is already stopped
- Stores CapturedRequest row
- Returns {"stored": true, "request_id": uuid}

FILE: backend/schemas/session.py
- Pydantic models: StartSessionRequest, StartSessionResponse, StopSessionRequest, StopSessionResponse, SessionListItem

FILE: backend/schemas/capture.py
- Pydantic model: CapturePayload with all fields matching the CapturedRequest model

Use async/await throughout. Use proper HTTP status codes. Add docstrings to every endpoint.
Output each file separately with the file path as a header.
```

---

### PROMPT 4 — mitmproxy addon + PII scrubber

```
You are implementing the network capture layer for TestGhost.

Write these files completely:

FILE: proxy/scrubber.py
- Class: PIIScrubber
- Method: scrub(data: dict) -> dict that recursively scrubs all string values
- Patterns to scrub: email, phone (Indian and international), JWT tokens (Bearer xxx), credit card numbers, Aadhaar numbers, PAN numbers, SSN, raw IP addresses in bodies
- Replace each match with a placeholder like [SCRUBBED_EMAIL]
- Never scrub URL paths themselves, only values
- Method: truncate_body(body: str, max_bytes=51200) -> str

FILE: proxy/addon.py
- mitmproxy addon class: TestGhostAddon
- __init__ reads SESSION_ID and BACKEND_URL from environment
- request() hook: extract method, url, path, headers (as dict), request body (decoded safely)
- response() hook: extract status_code, response_body (decoded safely), calculate response_time_ms
- Combine into payload dict, call scrubber.scrub(), then POST to BACKEND_URL/capture
- Use httpx for the POST (not requests — mitmproxy is async)
- Handle POST failures silently with a warning log — never crash the proxy

FILE: proxy/runner.py
- Function: start_proxy(session_id: str, port: int = 8080)
- Launches mitmdump as subprocess with -p port -s proxy/addon.py
- Sets SESSION_ID and BACKEND_URL as environment variables for the subprocess
- Returns the subprocess object so it can be killed later

Output each file separately with the file path as a header.
Add type hints throughout. Add error handling throughout.
```

---

### PROMPT 5 — Embedder + deduplicator

```
You are implementing the RAG deduplication layer for TestGhost.

Write these files completely:

FILE: ml/embedder.py
- Class: RequestEmbedder
- Loads sentence-transformers model "all-MiniLM-L6-v2" on init (cache to models/ directory)
- Method: build_embedding_string(method, path, request_body) -> str
  - Normalizes path parameters: /users/123 becomes /users/{id}
  - Extracts top-level JSON keys from request_body if it is valid JSON
  - Returns: "METHOD /normalized/path fields:key1,key2"
- Method: embed(method, path, request_body) -> list[float] (384 dimensions)

FILE: ml/deduplicator.py
- Class: Deduplicator
- Method: async is_duplicate(session_id, embedding_vector, db) -> tuple[bool, uuid | None]
- Runs pgvector cosine similarity query against embeddings table for the same session
- Returns (True, matching_id) if similarity > 0.92, else (False, None)
- Raw SQL query using pgvector <=> operator for cosine distance

FILE: ml/store_embedding.py
- async function: store_embedding(captured_request_id, embedding_vector, db)
- Inserts row into embeddings table
- Called only when is_duplicate returns False

Integrate into backend/routers/capture.py:
- Show exactly which lines to add to the /capture endpoint to call embedder and deduplicator
- If duplicate: set is_duplicate=True, duplicate_of_id=matching_id, skip embedding storage
- If not duplicate: store embedding

Output each file separately. Include the integration diff for capture.py.
```

---

### PROMPT 6 — Isolation Forest

```
You are implementing the anomaly detection layer for TestGhost.

Write these files completely:

FILE: ml/feature_extractor.py
- Function: extract_features(captured_request: CapturedRequest) -> list[float]
- Extracts exactly 6 features as floats:
  1. response_time_ms (capped at 10000)
  2. len(response_body) (capped at 100000)
  3. response_status (as float)
  4. count of top-level JSON keys in response_body (0 if not JSON)
  5. max nesting depth of response_body JSON (0 if not JSON, capped at 10)
  6. content_type_score: 1.0 for application/json, 0.5 for text/html, 0.0 for other
- Return [f1, f2, f3, f4, f5, f6] as normalized values between 0 and 1
- Normalization must be applied using the cap values above

FILE: ml/anomaly_detector.py
- Class: AnomalyDetector
- __init__: loads model from models/isolation_forest.pkl if it exists, else model is None
- Method: score(features: list[float]) -> float — returns decision_function score
- Method: is_anomaly(features: list[float]) -> bool — returns True if score < -0.1
- Method: is_ready() -> bool — returns True if model is loaded

FILE: ml/train_anomaly_model.py
- async function: train_model(db) -> None
- Loads all CapturedRequest rows where is_anomaly is NULL (unscored) and session count >= 50
- Extracts features for each
- Trains IsolationForest(contamination=0.1, random_state=42)
- Saves to models/isolation_forest.pkl using joblib
- Logs: "Model trained on N samples"

Integrate into backend/routers/capture.py:
- Show exactly which lines to add to score each incoming response
- If model is not ready: store anomaly_score=None, is_anomaly=False
- If model is ready: score, store anomaly_score and is_anomaly

Output each file separately. Include the integration additions for capture.py.
```

---

### PROMPT 7 — KMeans clusterer

```
You are implementing the semantic clustering layer for TestGhost.

Write this file completely:

FILE: ml/clusterer.py
- async function: cluster_session(session_id: uuid, db) -> dict[int, str]
- Loads all non-duplicate CapturedRequest rows for the session that have embeddings
- If fewer than 6 unique endpoints: assign all to cluster 0 labeled "general"
- Otherwise: load their embedding vectors from the embeddings table
- Try KMeans for k=2 to k=min(8, n_endpoints//2)
- Select k with highest silhouette_score
- Assign cluster labels using this heuristic:
  - Find the most common path prefix among endpoints in each cluster
  - Map common prefixes to labels: auth/login/token -> "auth", users/profile -> "users", admin -> "admin", else use the prefix itself
- Update cluster_id and cluster_label on each CapturedRequest row
- Return dict mapping cluster_id -> cluster_label
- Log the chosen k and silhouette score

Use sklearn KMeans and silhouette_score.
Handle edge cases: single endpoint, all duplicates, no embeddings.
Output the file with full error handling and type hints.
```

---

### PROMPT 8 — LangGraph 4-node agent

```
You are implementing the LangGraph test generation pipeline for TestGhost.
This is the most critical component. Be precise.

Write these files completely:

FILE: langgraph_pipeline/state.py
- TypedDict: AgentState with fields:
  - request: dict (the captured request data)
  - endpoint_type: str (auth/crud/admin/webhook/public)
  - risk_level: str (high/medium/low)
  - test_scenarios: list[dict] (each has: name, type, expected_status, description)
  - generated_code: str
  - validation_passed: bool
  - retry_count: int
  - error_message: str | None

FILE: langgraph_pipeline/prompts.py
- All prompts as Python string constants (not f-strings, use .format() placeholders)
- CLASSIFIER_SYSTEM: instructs the LLM to output JSON with endpoint_type and risk_level
- PLANNER_SYSTEM: instructs the LLM to output JSON list of test_scenarios
- WRITER_SYSTEM: instructs the LLM to output only valid Python pytest code, nothing else
- VALIDATOR_RETRY_SYSTEM: instructs the LLM to fix broken pytest code given the syntax error

FILE: langgraph_pipeline/nodes/classifier.py
- async function: classifier_node(state: AgentState) -> AgentState
- Calls Claude API with CLASSIFIER_SYSTEM prompt and the request dict as JSON in the user message
- Parses JSON response, updates state.endpoint_type and state.risk_level
- Falls back to "crud" and "low" if parsing fails

FILE: langgraph_pipeline/nodes/planner.py
- async function: planner_node(state: AgentState) -> AgentState
- Calls Claude API with PLANNER_SYSTEM prompt
- Always generates: 1 happy path test, 1 missing field test, 1 wrong type test
- If risk_level is high: also generates 1 auth bypass test
- If endpoint_type is auth: also generates 1 invalid credentials test
- Parses JSON response into state.test_scenarios

FILE: langgraph_pipeline/nodes/writer.py
- async function: writer_node(state: AgentState) -> AgentState
- Calls Claude API with WRITER_SYSTEM prompt
- User message includes: the full request dict, the full response dict, all test_scenarios
- Instructs Claude to use pytest.mark.parametrize for multiple scenarios
- Instructs Claude to assert: status code, specific response fields, response time if available
- Stores raw output in state.generated_code

FILE: langgraph_pipeline/nodes/validator.py
- async function: validator_node(state: AgentState) -> AgentState
- Runs ast.parse(state.generated_code)
- If passes: sets state.validation_passed = True
- If fails and state.retry_count < 2: increments retry_count, sets validation_passed = False, stores error in error_message
- If fails and retry_count >= 2: sets validation_passed = True with a comment in the code noting it needs review

FILE: langgraph_pipeline/graph.py
- Build the StateGraph
- Add all 4 nodes
- Edges: classifier -> planner -> writer -> validator
- Conditional edge from validator: if not validated and retry < 2, route back to writer, else END
- Compile and export as: test_generation_graph = graph.compile()

Output each file separately. Use async throughout. Add error handling to every node.
```

---

### PROMPT 9 — DeepEval grader + file writer

```
You are implementing the evaluation and output layer for TestGhost.

Write these files completely:

FILE: evaluation/grader.py
- Class: TestGrader
- Uses DeepEval to score generated pytest code
- Method: score(generated_code: str, original_request: dict, original_response: dict) -> dict
  Returns: {"coverage": float, "correctness": float, "edge_coverage": float, "overall": float, "reasoning": str}
- CoverageMetric: LLM-as-judge checks if all response fields present in original_response are asserted in generated_code
- CorrectnessMetric: checks that ast.parse passes AND at least 2 assert statements exist AND status code is asserted
- EdgeCoverageMetric: checks if at least one test scenario tests a non-200 status code path
- overall = (coverage + correctness + edge_coverage) / 3

FILE: evaluation/retry_controller.py
- Class: RetryController
- Method: async should_retry(score_result: dict, retry_count: int) -> bool
  Returns True if overall < 0.70 and retry_count < 2
- Method: build_retry_feedback(score_result: dict) -> str
  Returns a human-readable feedback string explaining why the test failed grading
  This feedback is injected into the next writer_node prompt

FILE: generation/file_writer.py
- Function: write_test_file(cluster_label: str, generated_code: str, output_dir: str) -> str
  Writes to output/tests/test_{cluster_label}.py
  Adds a header comment: # Generated by TestGhost — do not edit manually
  Returns the file path

FILE: generation/conftest_writer.py
- Function: write_conftest(cluster_labels: list[str], base_url: str, output_dir: str) -> str
  Writes output/tests/conftest.py
  Includes: base_url fixture, httpx AsyncClient fixture, auth_headers fixture stub
  Returns the file path

Output each file separately with full type hints and error handling.
```

---

### PROMPT 10 — HTML report + CLI wiring

```
You are implementing the reporting layer and CLI for TestGhost.

Write these files completely:

FILE: reporting/reporter.py
- Class: ReportGenerator
- Method: generate(session_id, db, output_dir) -> str (returns report file path)
- Loads: session metadata, all captured requests grouped by cluster, all generated tests with scores
- Computes: total_captured, unique_endpoints, duplicate_count, anomaly_count, cluster_breakdown (list of dicts), test_score_distribution
- Renders Jinja2 template from reporting/templates/report.html
- Saves to output/reports/report_{session_id}.html
- Returns the file path

FILE: reporting/templates/report.html
- Clean, readable HTML with inline CSS only (no external dependencies)
- Sections: summary bar (4 stats), cluster table (endpoints per cluster, test count, avg score), test list (file path, score, anomaly flag, high confidence badge), coverage gaps (endpoints with no test generated)
- Color coding: green for score > 0.9, yellow for 0.7-0.9, red for < 0.7
- No JavaScript required

FILE: backend/routers/generate.py
- POST /generate endpoint accepting session_id
- Orchestrates in order: clusterer -> for each cluster: langgraph_pipeline -> grader -> retry_controller -> file_writer -> conftest_writer -> reporter
- Returns: {"report_path": str, "test_files": list[str], "summary": dict}

FILE: cli/cli.py
- Click group: testghost
- testghost start --session NAME --port PORT(default 8080): starts FastAPI via uvicorn subprocess + proxy via proxy/runner.py, stores session_id in .testghost_session file
- testghost stop: reads session_id from .testghost_session, calls POST /session/stop, kills proxy subprocess
- testghost generate: reads session_id, calls POST /generate, prints report path
- testghost sessions: calls GET /sessions, prints table using tabulate

Output each file separately. The CLI must work as a real installed command via pyproject.toml entry point.
```

---

## PART 3 — FILE BATCHES (what to generate together)

| Batch | Files | Reason |
|---|---|---|
| Batch A | pyproject.toml, docker-compose.yml, .env.example, folder structure | Must exist before anything runs |
| Batch B | db/models.py, db/session.py, db/init_db.py, alembic/ | Everything depends on the schema |
| Batch C | routers/sessions.py, routers/capture.py, schemas/ | API surface must be stable before proxy is built |
| Batch D | proxy/addon.py, proxy/scrubber.py, proxy/runner.py | Proxy depends on /capture endpoint existing |
| Batch E | ml/embedder.py, ml/deduplicator.py, ml/store_embedding.py | RAG layer depends on embeddings table |
| Batch F | ml/feature_extractor.py, ml/anomaly_detector.py, ml/train_anomaly_model.py | Anomaly depends on captured_requests existing |
| Batch G | ml/clusterer.py | Depends on embeddings and captured_requests |
| Batch H | langgraph_pipeline/ (all 7 files) | Agent is self-contained but must be built together |
| Batch I | evaluation/grader.py, evaluation/retry_controller.py | Depends on LangGraph output |
| Batch J | generation/file_writer.py, generation/conftest_writer.py | Depends on grader output |
| Batch K | reporting/reporter.py, reporting/templates/report.html, routers/generate.py | Depends on all above |
| Batch L | cli/cli.py, pyproject.toml entry point | Wires everything — built last |

---

## PART 4 — VALIDATION CHECKLIST AFTER EACH BATCH

### After Batch A (scaffold)
- [ ] All directories exist with placeholder files
- [ ] `pip install -e .` completes without error
- [ ] `docker compose up -d` starts postgres on port 5432
- [ ] `psql -h localhost -U testghost -d testghost` connects successfully

### After Batch B (database)
- [ ] `alembic upgrade head` runs clean
- [ ] All 4 tables visible: `\dt` in psql
- [ ] pgvector extension active: `SELECT extname FROM pg_extension;`
- [ ] Insert one Session row manually and read it back

### After Batch C (API)
- [ ] `uvicorn backend.main:app --reload` starts
- [ ] `curl localhost:8000/health` returns 200
- [ ] POST /session/start returns a UUID
- [ ] POST /session/stop marks session complete
- [ ] POST /capture with a fake payload stores a row

### After Batch D (proxy)
- [ ] `mitmdump -p 8080 -s proxy/addon.py` starts without import errors
- [ ] Browser proxied through 8080 — one request appears in captured_requests
- [ ] A manually crafted payload with a fake email is scrubbed before storage
- [ ] Proxy failure (backend down) does not crash mitmproxy

### After Batch E (RAG)
- [ ] Embedding of `POST /api/users` is stored as 384-dim vector
- [ ] Same request sent twice — second is flagged as duplicate
- [ ] Different request is NOT flagged as duplicate
- [ ] pgvector query executes under 100ms

### After Batch F (anomaly)
- [ ] Feature extraction returns exactly 6 floats, all between 0 and 1
- [ ] Model trains on 50+ rows without error
- [ ] A 5000ms response scores as anomaly
- [ ] A normal 200ms response does not score as anomaly

### After Batch G (clustering)
- [ ] 20 endpoints cluster into 2-5 groups
- [ ] Cluster labels are human-readable strings
- [ ] captured_requests rows have cluster_id and cluster_label populated
- [ ] Silhouette score is logged

### After Batch H (LangGraph)
- [ ] Graph runs end-to-end on one request
- [ ] All 4 nodes are called (visible in logs)
- [ ] Output is valid Python (ast.parse passes)
- [ ] Retry triggers when validator receives broken syntax

### After Batch I (evaluation)
- [ ] Score dict has all 4 keys with float values
- [ ] Bad test (no assertions) scores below 0.70
- [ ] Good test scores above 0.70
- [ ] Retry feedback string is non-empty and describes the failure

### After Batch J (file output)
- [ ] `output/tests/test_auth.py` exists and is valid Python
- [ ] `output/tests/conftest.py` exists with base_url fixture
- [ ] Generated file has the TestGhost header comment

### After Batch K (report)
- [ ] `output/reports/report_{session_id}.html` exists
- [ ] Opening in browser shows real data (not empty template)
- [ ] Anomaly-flagged tests are highlighted differently
- [ ] High-confidence tests show green color

### After Batch L (CLI)
- [ ] `testghost start` launches both FastAPI and mitmproxy
- [ ] `testghost stop` stops the session and kills the proxy
- [ ] `testghost generate` produces test files and report
- [ ] `testghost sessions` prints a table of past sessions

---

## PART 5 — RED FLAGS — STOP AND MANUALLY REVIEW

These are the failure points that will waste days if ignored:

**RED FLAG 1: pgvector column type fails**
Symptom: SQLAlchemy migration error mentioning Vector type.
Fix: `pip install pgvector` and import `from pgvector.sqlalchemy import Vector`. Do not proceed until the embedding column exists and accepts a 384-dim list.

**RED FLAG 2: mitmproxy HTTPS returns empty bodies**
Symptom: Requests captured but request_body and response_body are always empty.
Fix: mitmproxy root CA is not installed in the browser. Every HTTPS body is encrypted and unreadable without the cert. Install it manually from `~/.mitmproxy/mitmproxy-ca-cert.pem`.

**RED FLAG 3: All requests flagged as duplicates**
Symptom: Every captured request has is_duplicate=True.
Fix: The embedding string is too generic. It must include path + method + body schema shape, not just the URL. Print the embedding string before embedding it to verify it is unique per endpoint.

**RED FLAG 4: LangGraph Writer generates valid syntax but wrong tests**
Symptom: ast.parse passes but tests assert wrong things (status code 201 on a GET, asserting a field that doesn't exist).
Fix: The Writer prompt is not including the actual response body. The prompt MUST contain the real captured response as a JSON string so Claude can assert real fields.

**RED FLAG 5: DeepEval scores everything 0.0**
Symptom: All tests rejected, infinite retry loop.
Fix: Your LLMTestCase is not constructed correctly. The `actual_output` field must be the full generated test code as a string. Print the test case before scoring and inspect it.

**RED FLAG 6: testghost generate hangs**
Symptom: CLI command never returns.
Fix: Add a 30-second asyncio timeout to every Claude API call. Without a timeout, a single slow or hanging LLM call blocks the entire pipeline indefinitely.

**RED FLAG 7: HTML report is blank**
Symptom: Report file exists but shows no data.
Fix: Print the Jinja2 context dict before rendering. The template variable names must match exactly. Jinja2 silently renders empty strings for missing variables.

**RED FLAG 8: Isolation Forest marks everything as anomaly after retraining**
Symptom: Every response after retraining has is_anomaly=True.
Fix: Your training data is too small or all the same. IsolationForest needs at least 100 diverse samples. Use contamination=0.1, not higher.

---

## PART 6 — MVP-FIRST PLAN vs V2 PLAN

---

### MVP (Weeks 1–4) — Ship this, nothing more

**What's in MVP:**
- mitmproxy capture with PII scrubbing
- FastAPI: /session/start, /capture, /session/stop, /generate
- SQLite instead of PostgreSQL (swap later — simpler local dev)
- Single Claude API call (no LangGraph — just one prompt per endpoint)
- Basic deduplication by URL+method exact match (no pgvector yet)
- pytest file output (no Jest)
- Plain text report (no HTML)
- CLI: testghost start, stop, generate

**What MVP proves:**
- The proxy captures real traffic
- The AI generates usable tests
- The file output is correct Python
- The whole flow is under 60 seconds

**What MVP does NOT have:**
- pgvector RAG
- LangGraph multi-agent
- Isolation Forest
- KMeans clustering
- DeepEval grading
- HTML report
- Docker

**Why this order:** You cannot know if the LangGraph prompts are correct until you have real captured traffic to feed them. Build capture first. Generate from real data. Then add intelligence layers.

---

### V2 (Weeks 5–8) — After MVP is proven

Add in this order:

1. **PostgreSQL + pgvector** — swap SQLite for real database, add embeddings table
2. **RAG deduplication** — replace exact-match with semantic deduplication
3. **LangGraph 4-node agent** — replace single Claude call with stateful agent
4. **Isolation Forest** — add anomaly detection after 100+ requests are captured
5. **KMeans clustering** — add after LangGraph is stable
6. **DeepEval grading** — add after test output is reliably valid Python
7. **HTML report** — add Jinja2 report after scoring works
8. **Jest output** — add JS test generation as a parallel Writer node
9. **Docker Compose** — containerize after everything runs locally

---

### V3 (Future — monetization)

- GitHub App integration (auto-run on PR)
- Team session sharing
- Slack notification when tests fail in CI
- Session diff: compare two sessions to detect API behaviour changes
- PyPI publish: `pip install testghost`

---

## PART 7 — FULL PRODUCTION FOLDER STRUCTURE

```
testghost/
├── pyproject.toml
├── .env.example
├── .env                          # gitignored
├── docker-compose.yml
├── README.md
├── CONTRIBUTING.md
│
├── proxy/
│   ├── addon.py                  # mitmproxy addon
│   ├── scrubber.py               # PII scrubbing
│   └── runner.py                 # subprocess launcher
│
├── backend/
│   ├── main.py                   # FastAPI app
│   ├── db/
│   │   ├── models.py             # SQLAlchemy ORM models
│   │   ├── session.py            # async DB connection
│   │   └── init_db.py            # table creation on startup
│   ├── routers/
│   │   ├── sessions.py           # /session/start, /stop, /sessions
│   │   ├── capture.py            # /capture
│   │   └── generate.py           # /generate — orchestration
│   └── schemas/
│       ├── session.py            # Pydantic models
│       └── capture.py            # Pydantic models
│
├── ml/
│   ├── embedder.py               # sentence-transformers
│   ├── deduplicator.py           # pgvector cosine similarity
│   ├── store_embedding.py        # insert to embeddings table
│   ├── feature_extractor.py      # 6 features for anomaly
│   ├── anomaly_detector.py       # Isolation Forest scoring
│   ├── train_anomaly_model.py    # model training script
│   └── clusterer.py              # KMeans clustering
│
├── langgraph_pipeline/
│   ├── state.py                  # AgentState TypedDict
│   ├── graph.py                  # StateGraph wiring
│   ├── prompts.py                # all LLM prompts
│   └── nodes/
│       ├── classifier.py         # node 1
│       ├── planner.py            # node 2
│       ├── writer.py             # node 3
│       └── validator.py          # node 4
│
├── evaluation/
│   ├── grader.py                 # DeepEval scoring
│   └── retry_controller.py      # retry logic
│
├── generation/
│   ├── file_writer.py            # writes test files
│   └── conftest_writer.py        # writes conftest.py
│
├── reporting/
│   ├── reporter.py               # HTML report generator
│   └── templates/
│       └── report.html           # Jinja2 template
│
├── cli/
│   └── cli.py                    # Click CLI
│
├── models/
│   ├── .gitkeep
│   └── isolation_forest.pkl      # gitignored after training
│
├── output/
│   ├── tests/                    # generated pytest files
│   └── reports/                  # generated HTML reports
│
├── tests/                        # TestGhost's own tests
│   ├── test_capture.py
│   ├── test_embedder.py
│   ├── test_anomaly.py
│   ├── test_langgraph.py
│   └── fixtures/
│       └── sample_requests.json  # synthetic captured requests
│
└── alembic/
    ├── env.py
    ├── script.py.mako
    └── versions/
        ├── 001_initial_schema.py
        ├── 002_add_duplicate_fields.py
        ├── 003_add_anomaly_fields.py
        └── 004_add_cluster_fields.py
```

---

## PART 8 — WHAT TO DO TODAY (RIGHT NOW)

1. Create the GitHub repo: `testghost` — private for now
2. Run Prompt 1 (scaffold) in Antigravity or Claude
3. Create the folder structure manually from the tree above
4. Copy `.env.example` and fill in your `ANTHROPIC_API_KEY`
5. Run `docker compose up -d` and confirm postgres starts
6. Run `pip install -e .` and confirm CLI entry point registers
7. Type `testghost --help` — it must print the command list without crashing

**If you do only these 7 things today, you are ready to start Day 2 tomorrow.**

That is the only goal for today. Not the proxy. Not the ML. Not LangGraph. The repo must run, the database must start, and the CLI must respond. Everything else builds on top of this.
