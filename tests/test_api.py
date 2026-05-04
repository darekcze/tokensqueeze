"""API smoke tests via FastAPI's TestClient (skipped if FastAPI missing)."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from server.main import app  # noqa: E402


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_compress_endpoint(client):
    r = client.post("/compress", json={
        "prompt": "Write a Python function that checks if a number is prime",
        "strategy": "sns",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["compressed"]
    assert body["tokens"]["compressed"] <= body["tokens"]["original"]


def test_stats_after_compress(client):
    client.post("/compress", json={"prompt": "hi please thank you", "strategy": "sns"})
    r = client.get("/stats")
    assert r.status_code == 200
    s = r.json()
    assert s["requests"] >= 1


def test_explain_returns_rules(client):
    r = client.post("/compress", json={
        "prompt": "Please write a function that returns the result as JSON",
        "strategy": "sns",
        "explain": True,
    })
    assert r.status_code == 200
    assert r.json()["rules_applied"]
