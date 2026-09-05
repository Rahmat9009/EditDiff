import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.main import DEFAULT_CORS_ORIGINS, get_cors_origins


def test_cors_origins_defaults_when_unset(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert get_cors_origins() == DEFAULT_CORS_ORIGINS
    assert get_cors_origins(None) == DEFAULT_CORS_ORIGINS


def test_cors_origins_single_production_origin():
    assert get_cors_origins("https://editdiff.vercel.app") == [
        "https://editdiff.vercel.app"
    ]


def test_cors_origins_multiple_comma_separated():
    raw = "https://editdiff.vercel.app,https://another-preview.example.com"
    expected = [
        "https://editdiff.vercel.app",
        "https://another-preview.example.com",
    ]
    assert get_cors_origins(raw) == expected


def test_cors_origins_whitespace_and_empty_entries():
    raw = "  https://editdiff.vercel.app  ,  ,  https://another-preview.example.com ,  "
    expected = [
        "https://editdiff.vercel.app",
        "https://another-preview.example.com",
    ]
    assert get_cors_origins(raw) == expected


def test_cors_origins_all_empty_or_whitespace_falls_back_to_defaults():
    assert get_cors_origins("") == DEFAULT_CORS_ORIGINS
    assert get_cors_origins("   ") == DEFAULT_CORS_ORIGINS
    assert get_cors_origins(" , ,   , ") == DEFAULT_CORS_ORIGINS


def test_cors_origins_reads_env_var(monkeypatch):
    monkeypatch.setenv(
        "CORS_ORIGINS",
        "https://editdiff.vercel.app, https://preview.vercel.app",
    )
    assert get_cors_origins() == [
        "https://editdiff.vercel.app",
        "https://preview.vercel.app",
    ]


def test_cors_local_defaults_accepted_by_app(client):
    # GET with allowed local origin
    res = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert res.status_code == 200
    assert res.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert res.headers.get("access-control-allow-credentials") == "true"

    # OPTIONS preflight
    preflight = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers.get("access-control-allow-origin") == "http://localhost:3000"

    # Unauthorized origin is rejected by CORS
    rejected = client.get("/health", headers={"Origin": "https://unauthorized.example.com"})
    assert rejected.status_code == 200
    assert "access-control-allow-origin" not in rejected.headers


def test_cors_production_origin_middleware():
    test_app = FastAPI()
    test_app.add_middleware(
        CORSMiddleware,
        allow_origins=get_cors_origins("https://editdiff.vercel.app, https://preview.vercel.app"),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @test_app.get("/test")
    def endpoint():
        return {"status": "ok"}

    with TestClient(test_app) as prod_client:
        allowed = prod_client.get("/test", headers={"Origin": "https://editdiff.vercel.app"})
        assert allowed.status_code == 200
        assert allowed.headers.get("access-control-allow-origin") == "https://editdiff.vercel.app"
        assert allowed.headers.get("access-control-allow-credentials") == "true"

        disallowed = prod_client.get("/test", headers={"Origin": "http://localhost:3000"})
        assert disallowed.status_code == 200
        assert "access-control-allow-origin" not in disallowed.headers
