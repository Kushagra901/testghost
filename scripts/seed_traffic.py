"""
TestGhost — Realistic traffic seeding script.
Generates 60 captured requests (55 normal, 5 anomalous outliers)
across multiple endpoint clusters (auth, users, products, orders).
Used to satisfy MIN_REQUESTS_FOR_ANOMALY_TRAINING (50) and test clustering.
"""

import asyncio
import json
import logging
import random
import uuid

from backend.db.models import CapturedRequest, Session, SessionStatus
from backend.db.session import AsyncSessionLocal
from ml.embedder import RequestEmbedder
from ml.store_embedding import store_embedding

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


ENDPOINT_TEMPLATES = [
    # Auth cluster
    ("POST", "/api/v1/auth/login", '{"username": "user{i}", "password": "secret{i}"}', 200, '{"token": "jwt_token_{i}"}'),
    ("POST", "/api/v1/auth/register", '{"email": "user{i}@example.com", "password": "secret{i}"}', 201, '{"id": {i}, "email": "user{i}@example.com"}'),
    ("POST", "/api/v1/auth/logout", None, 200, '{"status": "logged_out"}'),
    
    # Users cluster
    ("GET", "/api/v1/users/profile", None, 200, '{"id": {i}, "name": "User {i}", "role": "member"}'),
    ("GET", "/api/v1/users/{i}/account", None, 200, '{"account_id": {i}, "balance": 150.0}'),
    ("PUT", "/api/v1/users/{i}/settings", '{"theme": "dark", "notifications": true}', 200, '{"updated": true}'),

    # Products cluster
    ("GET", "/api/v1/products/catalog", None, 200, '{"items": [{"id": 1, "name": "Widget A"}, {"id": 2, "name": "Widget B"}]}'),
    ("GET", "/api/v1/products/{i}/detail", None, 200, '{"id": {i}, "title": "Product {i}", "price": 49.99}'),
    ("POST", "/api/v1/products/search", '{"query": "laptop", "category": "electronics"}', 200, '{"results": 15}'),

    # Orders cluster
    ("POST", "/api/v1/orders/cart/add", '{"product_id": {i}, "quantity": 1}', 200, '{"cart_total": 49.99}'),
    ("POST", "/api/v1/orders/checkout", '{"cart_id": {i}, "payment_method": "card"}', 201, '{"order_id": 100{i}, "status": "confirmed"}'),
    ("GET", "/api/v1/orders/{i}/status", None, 200, '{"order_id": 100{i}, "status": "shipped"}'),
]


async def seed_traffic(session_name: str = "audit_training_seed") -> uuid.UUID:
    """Seeds 60 requests with embeddings into PostgreSQL."""
    embedder = RequestEmbedder()

    async with AsyncSessionLocal() as db:
        session = Session(name=session_name, status=SessionStatus.COMPLETE)
        db.add(session)
        await db.flush()
        session_id = session.id
        logger.info("Created seed session: %s (%s)", session_name, session_id)

        requests = []
        # 1. Generate 55 normal requests
        for i in range(1, 56):
            tmpl = ENDPOINT_TEMPLATES[(i - 1) % len(ENDPOINT_TEMPLATES)]
            method, path_tmpl, req_b_tmpl, status, resp_b_tmpl = tmpl
            path = path_tmpl.replace("{i}", str(i))
            req_b = req_b_tmpl.replace("{i}", str(i)) if req_b_tmpl else None
            resp_b = resp_b_tmpl.replace("{i}", str(i))
            latency = round(random.uniform(25.0, 110.0), 2)

            req = CapturedRequest(
                session_id=session_id,
                method=method,
                path=path,
                url=f"https://api.example.com{path}",
                request_headers={"content-type": "application/json", "user-agent": "TestGhost-Seeder/1.0"},
                request_body=req_b,
                response_status=status,
                response_body=resp_b,
                response_headers={"content-type": "application/json"},
                response_time_ms=latency,
                is_duplicate=False,
                is_anomaly=False,
            )
            requests.append(req)

        # 2. Generate 5 anomalous outlier requests
        anomalous_definitions = [
            ("POST", "/api/v1/orders/checkout", '{"cart_id": 999}', 500, '{"error": "Internal Server Error: DB connection failed"}', 9500.0),
            ("GET", "/api/v1/reports/export", None, 504, '{"error": "Gateway Timeout"}', 14200.0),
            ("GET", "/api/v1/products/dump", None, 200, '{"data": "' + "x" * 70000 + '"}', 8200.0),
            ("POST", "/api/v1/auth/login", '{"username": "admin", "brute_force": true}', 502, '{"error": "Bad Gateway"}', 7800.0),
            ("GET", "/api/v1/analytics/stream", None, 500, '{"fatal": "Out of Memory"}', 11500.0),
        ]
        for method, path, req_b, status, resp_b, latency in anomalous_definitions:
            req = CapturedRequest(
                session_id=session_id,
                method=method,
                path=path,
                url=f"https://api.example.com{path}",
                request_headers={"content-type": "application/json"},
                request_body=req_b,
                response_status=status,
                response_body=resp_b,
                response_headers={"content-type": "application/json"},
                response_time_ms=latency,
                is_duplicate=False,
                is_anomaly=True,
            )
            requests.append(req)

        db.add_all(requests)
        await db.flush()

        # Compute and store embeddings for all requests
        for req in requests:
            vec = embedder.embed(req.method, req.path, req.request_body)
            await store_embedding(req.id, vec, db)

        await db.commit()
        logger.info("Successfully seeded %d captured requests with embeddings.", len(requests))
        return session_id


if __name__ == "__main__":
    sid = asyncio.run(seed_traffic())
    print(f"SEED_COMPLETE_SESSION_ID={sid}")
