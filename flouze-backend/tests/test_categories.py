import uuid

import pytest
from httpx import AsyncClient

BASE = "/api/v1"


async def _auth(client: AsyncClient, suffix: str) -> str:
    await client.post(f"{BASE}/auth/register", json={
        "email": f"cat{suffix}@test.com",
        "password": "password123",
        "display_name": f"Cat {suffix}",
    })
    resp = await client.post(f"{BASE}/auth/login", json={
        "email": f"cat{suffix}@test.com", "password": "password123",
    })
    return resp.json()["access_token"]


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Default categories (seeded at registration) ───────────────────────────────

@pytest.mark.asyncio
async def test_list_seeded_categories(client: AsyncClient):
    token = await _auth(client, "seed1")
    resp = await client.get(f"{BASE}/categories", headers=headers(token))
    assert resp.status_code == 200
    cats = resp.json()
    assert len(cats) == 6
    names = {c["name"] for c in cats}
    assert {"Alimentation", "Transport", "Logement", "Loisirs", "Santé", "Professionnel"} == names


@pytest.mark.asyncio
async def test_seeded_categories_have_correct_fields(client: AsyncClient):
    token = await _auth(client, "seed2")
    cats = (await client.get(f"{BASE}/categories", headers=headers(token))).json()
    alim = next(c for c in cats if c["name"] == "Alimentation")
    assert alim["emoji"] == "🛒"
    assert alim["color"] == "#2D5F3F"
    assert alim["archived_at"] is None


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_custom_category(client: AsyncClient):
    token = await _auth(client, "create1")
    resp = await client.post(f"{BASE}/categories", json={
        "name": "Voyages", "emoji": "✈️", "color": "#185FA5", "bg_color": "#E6F1FB",
    }, headers=headers(token))
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Voyages"
    assert body["emoji"] == "✈️"
    assert body["owner_id"] is not None
    assert body["space_id"] is None


@pytest.mark.asyncio
async def test_create_category_empty_name(client: AsyncClient):
    token = await _auth(client, "create_empty")
    resp = await client.post(f"{BASE}/categories", json={
        "name": "   ", "emoji": "✈️", "color": "#185FA5", "bg_color": "#E6F1FB",
    }, headers=headers(token))
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_category_appears_in_list(client: AsyncClient):
    token = await _auth(client, "create_list")
    await client.post(f"{BASE}/categories", json={
        "name": "Sport", "emoji": "🏋️", "color": "#0F6E56", "bg_color": "#E1F5EE",
    }, headers=headers(token))
    cats = (await client.get(f"{BASE}/categories", headers=headers(token))).json()
    assert any(c["name"] == "Sport" for c in cats)


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_category_name(client: AsyncClient):
    token = await _auth(client, "upd1")
    cats = (await client.get(f"{BASE}/categories", headers=headers(token))).json()
    cat_id = cats[0]["id"]
    resp = await client.patch(f"{BASE}/categories/{cat_id}", json={"name": "Renamed"}, headers=headers(token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


@pytest.mark.asyncio
async def test_update_category_partial(client: AsyncClient):
    token = await _auth(client, "upd2")
    cats = (await client.get(f"{BASE}/categories", headers=headers(token))).json()
    cat = cats[0]
    resp = await client.patch(
        f"{BASE}/categories/{cat['id']}", json={"emoji": "🎯"}, headers=headers(token)
    )
    assert resp.status_code == 200
    assert resp.json()["emoji"] == "🎯"
    assert resp.json()["name"] == cat["name"]  # unchanged


# ── Archive (soft delete) ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_archive_removes_from_active_list(client: AsyncClient):
    token = await _auth(client, "arch1")
    cats = (await client.get(f"{BASE}/categories", headers=headers(token))).json()
    cat_id = cats[0]["id"]

    resp = await client.delete(f"{BASE}/categories/{cat_id}", headers=headers(token))
    assert resp.status_code == 204

    active = (await client.get(f"{BASE}/categories", headers=headers(token))).json()
    assert cat_id not in {c["id"] for c in active}


@pytest.mark.asyncio
async def test_archived_visible_with_flag(client: AsyncClient):
    token = await _auth(client, "arch2")
    cats = (await client.get(f"{BASE}/categories", headers=headers(token))).json()
    cat_id = cats[0]["id"]

    await client.delete(f"{BASE}/categories/{cat_id}", headers=headers(token))

    archived = (await client.get(
        f"{BASE}/categories?include_archived=true", headers=headers(token)
    )).json()
    assert any(c["id"] == cat_id and c["archived_at"] is not None for c in archived)


# ── Access control ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_category_isolation_other_user_cannot_update(client: AsyncClient):
    token_a = await _auth(client, "iso_a1")
    token_b = await _auth(client, "iso_b1")
    cats_a = (await client.get(f"{BASE}/categories", headers=headers(token_a))).json()
    cat_id = cats_a[0]["id"]

    resp = await client.patch(
        f"{BASE}/categories/{cat_id}", json={"name": "Hacked"}, headers=headers(token_b)
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_category_not_found(client: AsyncClient):
    token = await _auth(client, "notfound_cat")
    resp = await client.patch(
        f"{BASE}/categories/{uuid.uuid4()}", json={"name": "X"}, headers=headers(token)
    )
    assert resp.status_code == 404
