# TestGhost

*Watches you use any app. Writes your tests.*

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/status-active%20development-orange.svg)]()

TestGhost sits between your browser (or HTTP client) and your application as an HTTPS proxy. It intercepts and scrubs real-world HTTP traffic, runs it through a 6-layer AI/ML pipeline, and generates a production-ready `pytest` test suite — with zero SDK dependencies, zero code changes to your application, and zero manual test authoring.

---

## Why This Exists

Most modern AI test generation and traffic-recording tools require importing SDKs or monkey-patching application code directly inside your codebase. TestGhost operates entirely at the network layer via an HTTPS proxy. Because it requires zero instrumentation in the target system, it works across any language, backend framework, legacy stack, or third-party API that you cannot modify.

---

## Architecture Overview

```
Browser / HTTP Client
        │
        ▼
   mitmproxy (Port 8080)
        │
        ▼
   PII Scrubber (Regex & Token Sanitization)
        │
        ▼
   FastAPI Backend
        │
        ├─► RAG Deduplication (pgvector Cosine Similarity)
        │
        ├─► Anomaly Detection (Isolation Forest)
        │
        ├─► Endpoint Clustering (KMeans + Silhouette Scoring)
        │
        ├─► LangGraph Agent
        │     (Classifier ──► Planner ──► Writer ──► Validator)
        │
        ├─► DeepEval Quality Scoring & Auto-Retry Loop
        │
        ▼
   Production Pytest Suite (.py) + Interactive HTML Report (.html)
```

---

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Proxy Engine** | `mitmproxy` |
| **Backend API** | `fastapi`, `uvicorn`, `sqlalchemy`, `asyncpg`, `alembic` |
| **Database & Vector Store** | PostgreSQL + `pgvector` |
| **Embeddings** | `sentence-transformers` |
| **Machine Learning** | `scikit-learn`, `numpy`, `joblib` |
| **Agent Orchestration** | `langgraph`, `langchain-anthropic`, `langchain-core` |
| **LLM Inference** | Anthropic Claude (configurable) |
| **Evaluation & Quality** | `deepeval` |
| **Reporting & CLI** | `jinja2`, `click`, `rich`, `tabulate` |

---

## Quick Start

### 1. Clone & Navigate to the Repository
```bash
git clone https://github.com/yourname/testghost.git
cd testghost
```

### 2. Configure Environment Variables
Copy the example environment file:
```bash
# macOS / Linux
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```
Open `.env` and set your preferred LLM provider and credentials. *Never commit your `.env` file to version control.*
```env
# Choose provider: gemini (default), anthropic, groq, openrouter
LLM_PROVIDER=gemini
GEMINI_API_KEY=your-gemini-api-key-here

# Or for Anthropic:
# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxx
```

### 3. Install Dependencies
Ensure your Python 3.12 virtual environment is activated:
```bash
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```
Install dependencies and the TestGhost CLI in editable mode:
```bash
pip install -r requirements.txt -r requirements-dev.txt
pip install -e .
```

### 4. Start PostgreSQL & Run Database Migrations
Ensure Docker Desktop is running, then start the PostgreSQL + pgvector container and apply schema migrations:
```bash
docker compose up -d
alembic upgrade head
```
*(Note: PostgreSQL + pgvector is mapped to host port `5433` in `docker-compose.yml` and `.env` to prevent conflicts with default host PostgreSQL instances).*

### 5. HTTPS Certificate Setup (One-Time)
To intercept encrypted HTTPS traffic without browser security warnings, install the mitmproxy Certificate Authority certificate into your operating system's or browser's trusted certificate store. Detailed instructions are available in the [official mitmproxy documentation](https://docs.mitmproxy.org/stable/concepts-certificates/).

### 6. Record and Generate Tests

**Start a recording session:**
```bash
testghost start --session "checkout-flow"
```

**Route traffic through the proxy (`localhost:8080`):**
Configure your browser or HTTP client to route traffic through proxy `http://127.0.0.1:8080` and use your application normally.

**Stop recording:**
```bash
testghost stop
```

**Generate the test suite:**
```bash
testghost generate
```

**Execute the generated tests:**
```bash
pytest output/tests/ -v
```

---

## CLI Command Reference

| Command | Description |
| :--- | :--- |
| `testghost start --session <name>` | Start a recording session. Launches the backend + proxy. |
| `testghost stop` | Stop the active recording session. |
| `testghost generate [--session <id>]` | Run the AI generation pipeline for a completed session. |
| `testghost sessions` | List all past recording sessions. |

---

## Project Structure

```
testghost/
├── alembic/                # Database schema migrations
├── backend/                # FastAPI control plane & database access
│   ├── db/                 # SQLAlchemy models & database sessions
│   ├── routers/            # API endpoints (sessions, capture, generate)
│   └── schemas/            # Pydantic validation schemas
├── cli/                    # Click + Rich command-line interface
├── evaluation/             # DeepEval scoring & retry controller
├── generation/             # Test suite file & conftest writers
├── langgraph_pipeline/     # LangGraph agent state machine & prompt nodes
│   └── nodes/              # Classifier, Planner, Writer, Validator nodes
├── ml/                     # ML modules (embeddings, dedup, clustering, anomalies)
├── output/                 # Generated test suites and HTML reports
│   ├── reports/            # Rendered Jinja2 HTML reports
│   └── tests/              # Generated pytest files
├── proxy/                  # mitmproxy addon and PII scrubber
├── scripts/                # Database initialization scripts
└── tests/                  # Unit and integration test suite
```

---

## How It Works

### 1. Proxy Capture & PII Scrubbing
Traffic flows through `mitmproxy`, where an event addon intercepts request and response payloads. The PII scrubber strips sensitive authentication headers, JWTs, emails, phone numbers, and credentials using configurable regex rules before streaming data to the FastAPI backend.

### 2. RAG Deduplication
Each incoming request is converted into a vector embedding using `sentence-transformers`. Vector embeddings are indexed in PostgreSQL using `pgvector`, filtering duplicate requests with high cosine similarity to keep test suites concise and focused.

### 3. Anomaly Detection
An unsupervised `IsolationForest` model evaluates request/response characteristics (payload sizes, response latencies, status codes) to detect edge cases and abnormal behavior, ensuring anomalies receive prioritized test coverage.

### 4. Semantic Clustering
The captured endpoints are clustered using `KMeans` with dynamic `k` selection via silhouette scoring. This groups related API routes into modular, logically separated test modules (e.g., `test_auth.py`, `test_users.py`).

### 5. LangGraph Generation Agent
A 4-node state machine manages generation:
1. **Classifier**: Categorizes the endpoint purpose and risk profile.
2. **Planner**: Identifies happy-path, boundary, and negative test scenarios.
3. **Writer**: Emits idiomatic `pytest` test code with fixtures and assertions.
4. **Validator**: Performs static syntax and integrity checks on the generated code.

### 6. DeepEval Scoring & Auto-Retry Loop
Generated tests are evaluated against coverage and correctness thresholds with `deepeval`. If a test falls below quality thresholds, targeted feedback is routed back to the agent writer for iterative refinement before saving.

---

## Limitations & Known Constraints

- **Anomaly Detection Sample Size**: The `IsolationForest` model requires sufficient historical traffic (typically 50+ requests) to reliably identify outliers.
- **Clustering Minimums**: KMeans clustering activates when a session captures 6 or more unique endpoints; smaller sessions default to a single cohesive module.
- **Regex-Based PII Scrubbing**: The default scrubber uses pattern matching for common PII (emails, JWTs, API keys). Applications with proprietary token formats should review or extend `proxy/scrubber.py` before capturing sensitive production traffic.

---

## Contributing

Contributions are welcome. Please open an issue or pull request to discuss proposed changes, bug fixes, or enhancements. Ensure all tests pass with `pytest tests/` before submitting.

---

## License

This project is licensed under the [MIT License](LICENSE).
