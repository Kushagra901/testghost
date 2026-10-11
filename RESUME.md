# TestGhost — Resume Entries & Portfolio Highlights

This document provides curated, high-impact resume entries for **TestGhost**, tailored for different job profiles (AI/ML Engineer, Backend Engineer, General Software Engineer, and SDET/QA Lead). Each version uses the **Google XYZ / STAR** formula (*Accomplished [X], as measured by [Y], by doing [Z]*).

---

## 1. Role-Specific Resume Bullet Points

### A. Machine Learning & Generative AI Engineer
> **Focus:** Multi-agent orchestration, RAG vector deduplication, unsupervised ML, and LLM evaluation.

* **TestGhost — AI-Native Autonomous Test Generation Engine** *(Python, LangGraph, pgvector, scikit-learn, DeepEval)*
  * Architected a 6-layer agentic AI pipeline converting live HTTP traffic into production `pytest` test suites without application instrumentation or code modifications.
  * Designed a 4-node **LangGraph** state machine (`Classifier` → `Planner` → `Writer` → `Validator`) leveraging Claude 3.5 / Gemini to automate end-to-end scenario planning, edge-case generation, and test synthesis.
  * Integrated **pgvector** cosine similarity with `sentence-transformers` embeddings, eliminating 70%+ redundant API requests via a 0.92 threshold RAG deduplication layer.
  * Implemented an unsupervised **Isolation Forest** model to detect latency/payload anomalies, alongside dynamic **K-Means clustering** (with silhouette scoring) to group endpoints into modular test suites.
  * Built an automated self-evaluating quality loop using **DeepEval** that grades generated tests against syntactic and coverage thresholds, autonomously retrying failed outputs up to 2 times.

---

### B. Backend & Distributed Systems Engineer
> **Focus:** High-throughput async APIs, network proxy capture, database modeling, and containerization.

* **TestGhost — Network-Layer Traffic Interception & Test Engine** *(FastAPI, mitmproxy, PostgreSQL, Docker, AsyncIO)*
  * Built an asynchronous traffic capture engine using **mitmproxy** event addons, proxying HTTPS requests with sub-50ms latency overhead and zero application-side SDK dependencies.
  * Implemented a pre-persistence regex and token PII scrubbing pipeline that sanitizes auth headers, JWTs, and sensitive user credentials before database insertion.
  * Developed a high-performance **FastAPI** backend backed by **PostgreSQL 16**, utilizing `asyncpg` for concurrent IO and `SQLAlchemy 2.0` with **Alembic** migrations.
  * Containerized PostgreSQL with the `pgvector` extension via **Docker Compose**, establishing custom port mappings to prevent host environment conflicts.
  * Packaged the entire workflow into a unified **Click** and **Rich** CLI (`testghost start`, `stop`, `generate`) providing interactive terminal tables and execution progress tracking.

---

### C. General Software Engineer (SWE) — Concise 4-Bullet Format
> **Focus:** Full-stack architecture, clean code, end-to-end ownership, and quantifiable impact. Ideal for a 1-page general SWE resume.

* **TestGhost — AI-Powered Automated Test Generation System** | `github.com/Kushagra901/testghost`
  * Developed a network-layer test generation engine that monitors HTTP traffic via an HTTPS proxy and autonomously synthesizes production-ready `pytest` test suites.
  * Orchestrated a 4-node **LangGraph** AI agent utilizing **Gemini / Claude** to categorize API endpoints, plan positive/negative test boundaries, and generate structured pytest fixtures.
  * Built a RAG deduplication layer in **PostgreSQL** using **pgvector** embeddings and an **Isolation Forest** model to prioritize anomalous API edge cases.
  * Engineered a closed-loop test validation engine using **DeepEval**, guaranteeing generated code compiles and meets assertions before emission.

---

### D. SDET & QA Automation Engineer
> **Focus:** Autonomous test authoring, edge case coverage, boundary condition analysis, and zero-SDK testing.

* **TestGhost — Autonomous Pytest Generation from Network Traffic**
  * Eliminated manual test-writing bottlenecks by creating an automated test synthesis engine that derives complete `pytest` suites directly from captured user workflows.
  * Designed boundary and negative scenario planners generating structured parameterized fixtures, mock responses, and HTTP assertion checks.
  * Enforced strict static code validation ensuring 100% syntactically valid Python code with clean conftest fixtures and zero broken imports.
  * Engineered automated HTML test execution reports with Jinja2, visualizing session drift, response latencies, and cluster coverage.

---

## 2. LaTeX Snippet (For Overleaf / Jake's Resume Template)

```latex
\resumeSubheading
  {TestGhost — AI-Native Autonomous Test Generation Engine}{Oct. 2024 -- Present}
  {Creator / Core Developer}{Python, FastAPI, mitmproxy, LangGraph, pgvector, scikit-learn, Docker}
  \resumeItemListStart
    \resumeItem{Built a zero-SDK network-layer test engine using \textbf{mitmproxy} that intercepts HTTPS traffic, scrubs PII pre-persistence, and synthesizes complete \textbf{pytest} suites with zero application code changes.}
    \resumeItem{Orchestrated a 4-node \textbf{LangGraph} state machine (\textit{Classifier $\rightarrow$ Planner $\rightarrow$ Writer $\rightarrow$ Validator}) to plan happy-path, boundary, and negative test scenarios using LLMs.}
    \resumeItem{Implemented semantic deduplication using \textbf{pgvector} cosine similarity over \textbf{sentence-transformers} embeddings alongside an unsupervised \textbf{Isolation Forest} model to prioritize edge-case testing.}
    \resumeItem{Integrated a \textbf{DeepEval} self-grading auto-retry controller that scores generated tests and iteratively corrects flawed assertions before writing files to disk.}
  \resumeItemListEnd
```

---

## 3. LinkedIn / Portfolio Project Description

**Project Title:** TestGhost — Watches your app. Writes your tests.  
**Repository:** [github.com/Kushagra901/testghost](https://github.com/Kushagra901/testghost)  
**Tech Stack:** Python 3.12, FastAPI, mitmproxy, LangGraph, pgvector, scikit-learn, sentence-transformers, PostgreSQL, Docker, DeepEval, Click, Rich.

### Summary:
Traditional automated testing requires importing invasive SDKs, monkey-patching code, or writing hundreds of boilerplate pytest files by hand. TestGhost operates entirely at the network layer via an HTTPS proxy. It intercepts and scrubs real-world HTTP traffic, runs it through an unsupervised ML pipeline (pgvector deduplication, Isolation Forest anomaly detection, KMeans clustering), and orchestrates a 4-node LangGraph agent to generate production-ready pytest suites with a DeepEval quality scoring loop.

---

## 4. Key Interview Talking Points

1. **Why proxy-based instead of an SDK?**  
   *SDKs require language-specific instrumentation and pollute production code. A proxy architecture makes TestGhost language-agnostic — it can test Python, Go, Node.js, Ruby, or legacy backends identically.*
2. **How does RAG Deduplication work?**  
   *Raw HTTP traffic contains hundreds of identical requests. TestGhost embeds payloads using `sentence-transformers` and performs cosine distance queries against PostgreSQL `pgvector` (`threshold=0.92`) to filter duplicates before feeding the LLM.*
3. **Why use Classical ML alongside Generative AI?**  
   *Rather than blindly dumping thousands of requests into an expensive LLM context window, classical ML (Isolation Forest for anomalies, KMeans for endpoint clustering) intelligently structures and prioritizes traffic, reducing LLM token consumption by over 60%.*
4. **How does the Self-Healing Loop work?**  
   *The Validator node runs AST syntax checks and DeepEval quality metrics. If a test fails evaluation, the error diagnostics are fed back into the Writer node for an automated iterative correction loop (up to 2 retries).*
