import uuid

import pytest
from httpx import AsyncClient

BASE = "/api/v1"


async def _auth(client: AsyncClient, suffix: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={
        "email": f"exp{suffix}@test.com",
        "password": "password123",
        "display_name": f"Exp {suffix}",
    })
    resp = await client.post(f"{BASE}/auth/login", json={
        "email": f"exp{suffix}@test.com", "password": "password123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def payload(**kwargs) -> dict:
    return {"title": "Test dépense", "amount": "100.00", "currency": "MAD",
            "date": "2026-05-15", **kwargs}


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_expense_mad(client: AsyncClient):
    h = await _auth(client, "c1")
    resp = await client.post(f"{BASE}/expenses", json=payload(), headers=h)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Test dépense"
    assert body["amount"] == "100.00"
    assert body["currency"] == "MAD"
    assert body["amount_mad"] == "100.00"
    assert body["exchange_rate"] is None  # same currency → no rate stored


@pytest.mark.asyncio
async def test_create_expense_foreign_currency(client: AsyncClient):
    """EUR → MAD conversion (fallback rate=1.0 in tests, no API key)."""
    h = await _auth(client, "c2")
    resp = await client.post(f"{BASE}/expenses", json=payload(amount="50.00", currency="EUR"), headers=h)
    assert resp.status_code == 201
    body = resp.json()
    assert body["currency"] == "EUR"
    assert body["amount"] == "50.00"
    assert body["amount_mad"] is not None  # calculated


@pytest.mark.asyncio
async def test_create_expense_negative_amount(client: AsyncClient):
    h = await _auth(client, "c3")
    resp = await client.post(f"{BASE}/expenses", json=payload(amount="-10"), headers=h)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_expense_zero_amount(client: AsyncClient):
    h = await _auth(client, "c4")
    resp = await client.post(f"{BASE}/expenses", json=payload(amount="0"), headers=h)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_expense_empty_title(client: AsyncClient):
    h = await _auth(client, "c5")
    resp = await client.post(f"{BASE}/expenses", json=payload(title="  "), headers=h)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_expense_with_note(client: AsyncClient):
    h = await _auth(client, "c6")
    resp = await client.post(f"{BASE}/expenses", json=payload(note="Détail optionnel"), headers=h)
    assert resp.status_code == 201
    assert resp.json()["note"] == "Détail optionnel"


# ── List & filters ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_list_expenses(client: AsyncClient):
    h = await _auth(client, "l1")
    await client.post(f"{BASE}/expenses", json=payload(title="Dépense A"), headers=h)
    await client.post(f"{BASE}/expenses", json=payload(title="Dépense B"), headers=h)
    resp = await client.get(f"{BASE}/expenses", headers=h)
    assert resp.status_code == 200
    titles = {e["title"] for e in resp.json()}
    assert {"Dépense A", "Dépense B"}.issubset(titles)


@pytest.mark.asyncio
async def test_filter_by_month(client: AsyncClient):
    h = await _auth(client, "l2")
    await client.post(f"{BASE}/expenses", json=payload(title="Mai",  date="2026-05-10"), headers=h)
    await client.post(f"{BASE}/expenses", json=payload(title="Juin", date="2026-06-01"), headers=h)

    resp = await client.get(f"{BASE}/expenses?month=2026-05", headers=h)
    titles = {e["title"] for e in resp.json()}
    assert "Mai" in titles
    assert "Juin" not in titles


@pytest.mark.asyncio
async def test_filter_by_search(client: AsyncClient):
    h = await _auth(client, "l3")
    await client.post(f"{BASE}/expenses", json=payload(title="Carrefour courses"), headers=h)
    await client.post(f"{BASE}/expenses", json=payload(title="Uber taxi"), headers=h)

    resp = await client.get(f"{BASE}/expenses?q=carrefour", headers=h)
    titles = {e["title"] for e in resp.json()}
    assert "Carrefour courses" in titles
    assert "Uber taxi" not in titles


@pytest.mark.asyncio
async def test_filter_case_insensitive(client: AsyncClient):
    h = await _auth(client, "l4")
    await client.post(f"{BASE}/expenses", json=payload(title="Marjane courses"), headers=h)
    resp = await client.get(f"{BASE}/expenses?q=MARJANE", headers=h)
    assert any("Marjane" in e["title"] for e in resp.json())


@pytest.mark.asyncio
async def test_pagination(client: AsyncClient):
    h = await _auth(client, "l5")
    for i in range(5):
        await client.post(f"{BASE}/expenses", json=payload(title=f"Dep {i}"), headers=h)

    page1 = (await client.get(f"{BASE}/expenses?limit=3&offset=0", headers=h)).json()
    page2 = (await client.get(f"{BASE}/expenses?limit=3&offset=3", headers=h)).json()
    assert len(page1) == 3
    assert len(page2) >= 2
    assert {e["id"] for e in page1}.isdisjoint({e["id"] for e in page2})


# ── Update ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_expense(client: AsyncClient):
    h = await _auth(client, "u1")
    created = (await client.post(f"{BASE}/expenses", json=payload(), headers=h)).json()

    resp = await client.patch(
        f"{BASE}/expenses/{created['id']}",
        json={"title": "Modifiée", "amount": "250.00"},
        headers=h,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Modifiée"
    assert resp.json()["amount"] == "250.00"
    assert resp.json()["amount_mad"] == "250.00"


@pytest.mark.asyncio
async def test_update_expense_not_found(client: AsyncClient):
    h = await _auth(client, "u2")
    resp = await client.patch(
        f"{BASE}/expenses/{uuid.uuid4()}", json={"title": "X"}, headers=h
    )
    assert resp.status_code == 404


# ── Soft delete ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_expense_removes_from_list(client: AsyncClient):
    h = await _auth(client, "d1")
    created = (await client.post(f"{BASE}/expenses", json=payload(), headers=h)).json()

    resp = await client.delete(f"{BASE}/expenses/{created['id']}", headers=h)
    assert resp.status_code == 204

    expenses = (await client.get(f"{BASE}/expenses", headers=h)).json()
    assert created["id"] not in {e["id"] for e in expenses}


@pytest.mark.asyncio
async def test_delete_then_update_returns_404(client: AsyncClient):
    h = await _auth(client, "d2")
    created = (await client.post(f"{BASE}/expenses", json=payload(), headers=h)).json()
    await client.delete(f"{BASE}/expenses/{created['id']}", headers=h)

    resp = await client.patch(
        f"{BASE}/expenses/{created['id']}", json={"title": "Ghost"}, headers=h
    )
    assert resp.status_code == 404


# ── Access control ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_expense_isolation_other_user_cannot_delete(client: AsyncClient):
    h_a = await _auth(client, "iso_e_a")
    h_b = await _auth(client, "iso_e_b")
    created = (await client.post(f"{BASE}/expenses", json=payload(), headers=h_a)).json()

    resp = await client.delete(f"{BASE}/expenses/{created['id']}", headers=h_b)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_expense_isolation_other_user_cannot_update(client: AsyncClient):
    h_a = await _auth(client, "iso_e_c")
    h_b = await _auth(client, "iso_e_d")
    created = (await client.post(f"{BASE}/expenses", json=payload(), headers=h_a)).json()

    resp = await client.patch(
        f"{BASE}/expenses/{created['id']}", json={"title": "Hacked"}, headers=h_b
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_expense_not_in_other_users_list(client: AsyncClient):
    h_a = await _auth(client, "iso_e_e")
    h_b = await _auth(client, "iso_e_f")
    created = (await client.post(f"{BASE}/expenses", json=payload(), headers=h_a)).json()

    expenses_b = (await client.get(f"{BASE}/expenses", headers=h_b)).json()
    assert created["id"] not in {e["id"] for e in expenses_b}
