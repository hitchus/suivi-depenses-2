"""
Tests for authentication endpoints.
Requires: flouze_test PostgreSQL database (see conftest.py header).
"""

import pytest
from httpx import AsyncClient

BASE = "/api/v1"


def user_payload(suffix: str = "1") -> dict:
    return {
        "email": f"user{suffix}@example.com",
        "password": "password123",
        "display_name": f"User {suffix}",
    }


# ── Register ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post(f"{BASE}/auth/register", json=user_payload("reg1"))
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_seeds_default_categories(client: AsyncClient):
    """After registration, the user should have 6 default categories."""
    resp = await client.post(f"{BASE}/auth/register", json=user_payload("reg_cat"))
    assert resp.status_code == 201
    token = resp.json()["access_token"]

    cats = await client.get(f"{BASE}/categories", headers={"Authorization": f"Bearer {token}"})
    # categories endpoint will be added in Jalon 4 — test is a placeholder
    # assert cats.status_code == 200
    # assert len(cats.json()) == 6


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    await client.post(f"{BASE}/auth/register", json=user_payload("dup"))
    resp = await client.post(f"{BASE}/auth/register", json=user_payload("dup"))
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_register_weak_password(client: AsyncClient):
    payload = user_payload("weak")
    payload["password"] = "short"
    resp = await client.post(f"{BASE}/auth/register", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    payload = user_payload("invalid")
    payload["email"] = "not-an-email"
    resp = await client.post(f"{BASE}/auth/register", json=payload)
    assert resp.status_code == 422


# ── Login ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    p = user_payload("login1")
    await client.post(f"{BASE}/auth/register", json=p)

    resp = await client.post(f"{BASE}/auth/login", json={"email": p["email"], "password": p["password"]})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    # refresh token cookie set
    assert "refresh_token" in resp.cookies


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    p = user_payload("login2")
    await client.post(f"{BASE}/auth/register", json=p)

    resp = await client.post(f"{BASE}/auth/login", json={"email": p["email"], "password": "wrongpass"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_email(client: AsyncClient):
    resp = await client.post(
        f"{BASE}/auth/login", json={"email": "nobody@example.com", "password": "password123"}
    )
    assert resp.status_code == 401


# ── Refresh ───────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_success(client: AsyncClient):
    p = user_payload("refresh1")
    await client.post(f"{BASE}/auth/register", json=p)
    login = await client.post(f"{BASE}/auth/login", json={"email": p["email"], "password": p["password"]})
    refresh_token = login.cookies["refresh_token"]

    resp = await client.post(
        f"{BASE}/auth/refresh",
        cookies={"refresh_token": refresh_token},
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_refresh_invalid_token(client: AsyncClient):
    resp = await client.post(
        f"{BASE}/auth/refresh",
        cookies={"refresh_token": "00000000-0000-0000-0000-000000000000"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_missing_cookie(client: AsyncClient):
    resp = await client.post(f"{BASE}/auth/refresh")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    """Using a refresh token twice should fail the second time (rotation)."""
    p = user_payload("rotation1")
    await client.post(f"{BASE}/auth/register", json=p)
    login = await client.post(f"{BASE}/auth/login", json={"email": p["email"], "password": p["password"]})
    rt = login.cookies["refresh_token"]

    first = await client.post(f"{BASE}/auth/refresh", cookies={"refresh_token": rt})
    assert first.status_code == 200

    second = await client.post(f"{BASE}/auth/refresh", cookies={"refresh_token": rt})
    assert second.status_code == 401


# ── Logout ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    p = user_payload("logout1")
    await client.post(f"{BASE}/auth/register", json=p)
    login = await client.post(f"{BASE}/auth/login", json={"email": p["email"], "password": p["password"]})
    rt = login.cookies["refresh_token"]

    resp = await client.post(f"{BASE}/auth/logout", cookies={"refresh_token": rt})
    assert resp.status_code == 204

    # Refresh after logout must fail
    after = await client.post(f"{BASE}/auth/refresh", cookies={"refresh_token": rt})
    assert after.status_code == 401


# ── GET /users/me ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_me_success(client: AsyncClient):
    p = user_payload("me1")
    await client.post(f"{BASE}/auth/register", json=p)
    login = await client.post(f"{BASE}/auth/login", json={"email": p["email"], "password": p["password"]})
    token = login.json()["access_token"]

    resp = await client.get(f"{BASE}/users/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == p["email"]
    assert body["display_name"] == p["display_name"]
    assert "id" in body


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get(f"{BASE}/users/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me_invalid_token(client: AsyncClient):
    resp = await client.get(f"{BASE}/users/me", headers={"Authorization": "Bearer invalid.token.here"})
    assert resp.status_code == 401
