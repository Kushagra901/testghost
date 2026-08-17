"""
All LLM prompts for TestGhost as module-level string constants.
Use .format(**kwargs) — not f-strings — to interpolate values.
"""

CLASSIFIER_SYSTEM = """\
You are an API endpoint classifier. Given an HTTP request and response, output a JSON object:
{{"endpoint_type": "<type>", "risk_level": "<level>"}}

endpoint_type must be one of: auth, crud, admin, webhook, public
- auth: login, logout, token refresh, registration, password reset
- crud: create/read/update/delete operations on data resources
- admin: admin panel, management, staff-only operations
- webhook: callbacks, event notifications, external integrations
- public: health checks, static content, unauthenticated reads

risk_level must be one of: high, medium, low
- high: auth endpoints, admin operations, payment processing
- medium: write operations on user data, state-changing actions
- low: read-only, public, health check endpoints

Output ONLY the JSON object. No explanation. No markdown.
"""

CLASSIFIER_USER = """\
Classify this endpoint:
Method: {method}
Path: {path}
Request body: {request_body}
Response status: {response_status}
Response body (first 500 chars): {response_body_preview}
"""

PLANNER_SYSTEM = """\
You are a test scenario planner. Given an HTTP endpoint's type and risk level,
output a JSON array of test scenarios. Each scenario is:
{{"name": "<test_name>", "type": "<scenario_type>", "expected_status": <int>, "description": "<what to test>"}}

Always include:
1. happy_path: the normal successful case
2. missing_required_field: omit one required body field
3. wrong_type: send wrong data type for a field

If risk_level is "high", also add:
4. unauthorized: test without auth headers, expect 401 or 403

If endpoint_type is "auth", also add:
4. invalid_credentials: wrong password or expired token

Output ONLY the JSON array. No markdown. No explanation.
"""

PLANNER_USER = """\
Plan test scenarios for:
endpoint_type: {endpoint_type}
risk_level: {risk_level}
method: {method}
path: {path}
observed request body: {request_body}
observed response status: {response_status}
observed response body (first 300 chars): {response_body_preview}
"""

WRITER_SYSTEM = """\
You are a pytest test writer. Write a complete, valid pytest file for the given test scenarios.

Rules:
- Use pytest.mark.parametrize for multiple scenarios
- Use httpx.Client for HTTP calls, base_url from a conftest.py fixture
- Assert: exact status code, at least 2 specific response body fields
- Include the real observed request body and response fields in your assertions
- Use realistic variable names
- Add a docstring to each test function
- Do NOT use mocking — these are real integration tests
- Do NOT add imports that are not in the standard library or pytest/httpx
- Output ONLY valid Python code. No markdown. No explanation. No ```python blocks.
"""

WRITER_USER = """\
Write pytest integration tests for this captured HTTP interaction:

METHOD: {method}
PATH: {path}
REQUEST BODY: {request_body}
RESPONSE STATUS: {response_status}
RESPONSE BODY: {response_body}
RESPONSE TIME MS: {response_time_ms}
IS ANOMALY: {is_anomaly}

TEST SCENARIOS TO IMPLEMENT:
{scenarios_json}

Base URL comes from a conftest.py fixture called `base_url` (string).
Write all scenarios in a single parametrized test function.
"""

WRITER_RETRY_SYSTEM = """\
You are fixing a broken pytest file. The previous attempt had this problem:
{error_message}

Here is the broken code:
{broken_code}

Fix ONLY the syntax/logic error described. Keep all test scenarios.
Output ONLY the corrected Python code. No markdown. No explanation.
"""

VALIDATOR_FEEDBACK_TEMPLATE = """\
The generated test failed quality evaluation.

Coverage score: {coverage:.2f} (need >= 0.70)
Correctness score: {correctness:.2f} (need >= 0.70)
Edge coverage score: {edge_coverage:.2f} (need >= 0.70)
Overall score: {overall:.2f}

Problems identified:
{reasoning}

Rewrite the test to fix these issues. Keep the same endpoint and scenarios.
"""
