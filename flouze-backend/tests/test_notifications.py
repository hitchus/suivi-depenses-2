import pytest
from httpx import AsyncClient

BASE = "/api/v1"
MONTH = "2026-05"


async def _auth(client: AsyncClient, suffix: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={
        "email": f"notif{suffix}@test.com",
        "password": "password123",
        "display_name": f"Notif {suffix}",
    })
    resp = await client.post(f"{BASE}/auth/login", json={
        "email": f"notif{suffix}@test.com", "password": "password123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _first_category_id(client: AsyncClient, headers: dict) -> str:
    cats = (await client.get(f"{BASE}/categories", headers=headers)).json()
    return cats[0]["id"]


# ── List notifications ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_notifications(client: AsyncClient):
    h = await _auth(client, "empty1")
    resp = await client.get(f"{BASE}/notifications", headers=h)
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_notifications_isolated_per_user(client: AsyncClient):
    h1 = await _auth(client, "iso1")
    h2 = await _auth(client, "iso2")
    cat_id = await _first_category_id(client, h1)

    # user1 creates a budget then exceeds it → gets notification
    await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "10"}, headers=h1)
    await client.post(f"{BASE}/expenses", json={
        "title": "Over budget", "amount": "50", "currency": "MAD",
        "date": "2026-05-01", "category_id": cat_id,
    }, headers=h1)

    # user2 should see no notifications
    resp2 = await client.get(f"{BASE}/notifications", headers=h2)
    assert resp2.json() == []


# ── Budget alert ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_budget_alert_created_when_exceeded(client: AsyncClient):
    h = await _auth(client, "alert1")
    cat_id = await _first_category_id(client, h)

    await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "100"}, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "Dépassement", "amount": "150", "currency": "MAD",
        "date": "2026-05-10", "category_id": cat_id,
    }, headers=h)

    notifs = (await client.get(f"{BASE}/notifications", headers=h)).json()
    budget_alerts = [n for n in notifs if n["type"] == "BUDGET_ALERT"]
    assert len(budget_alerts) >= 1
    alert = budget_alerts[0]
    assert alert["payload"]["category_id"] == cat_id
    assert float(alert["payload"]["budget"]) == pytest.approx(100, abs=1)
    assert float(alert["payload"]["spent"]) > 100


@pytest.mark.asyncio
async def test_no_alert_when_under_budget(client: AsyncClient):
    h = await _auth(client, "noalert1")
    cat_id = await _first_category_id(client, h)

    await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "1000"}, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "Small", "amount": "50", "currency": "MAD",
        "date": "2026-05-10", "category_id": cat_id,
    }, headers=h)

    notifs = (await client.get(f"{BASE}/notifications", headers=h)).json()
    assert not any(n["type"] == "BUDGET_ALERT" for n in notifs)


@pytest.mark.asyncio
async def test_no_alert_without_budget(client: AsyncClient):
    h = await _auth(client, "nobud1")
    cat_id = await _first_category_id(client, h)

    # No budget set — no alert expected even for large expense
    await client.post(f"{BASE}/expenses", json={
        "title": "No budget", "amount": "9999", "currency": "MAD",
        "date": "2026-05-05", "category_id": cat_id,
    }, headers=h)

    notifs = (await client.get(f"{BASE}/notifications", headers=h)).json()
    assert not any(n["type"] == "BUDGET_ALERT" for n in notifs)


# ── Mark as read ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mark_notification_as_read(client: AsyncClient):
    h = await _auth(client, "read1")
    cat_id = await _first_category_id(client, h)

    await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "10"}, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "Over", "amount": "20", "currency": "MAD",
        "date": "2026-05-01", "category_id": cat_id,
    }, headers=h)

    notifs = (await client.get(f"{BASE}/notifications", headers=h)).json()
    assert len(notifs) >= 1
    notif_id = notifs[0]["id"]
    assert notifs[0]["read_at"] is None

    resp = await client.patch(f"{BASE}/notifications/{notif_id}/read", headers=h)
    assert resp.status_code == 200
    assert resp.json()["read_at"] is not None


@pytest.mark.asyncio
async def test_mark_read_idempotent(client: AsyncClient):
    h = await _auth(client, "read2")
    cat_id = await _first_category_id(client, h)

    await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "5"}, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "Over2", "amount": "10", "currency": "MAD",
        "date": "2026-05-01", "category_id": cat_id,
    }, headers=h)

    notifs = (await client.get(f"{BASE}/notifications", headers=h)).json()
    notif_id = notifs[0]["id"]

    r1 = await client.patch(f"{BASE}/notifications/{notif_id}/read", headers=h)
    r2 = await client.patch(f"{BASE}/notifications/{notif_id}/read", headers=h)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["read_at"] == r2.json()["read_at"]


@pytest.mark.asyncio
async def test_mark_read_wrong_user_returns_404(client: AsyncClient):
    h_owner = await _auth(client, "wrong1")
    h_other = await _auth(client, "wrong2")
    cat_id = await _first_category_id(client, h_owner)

    await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "1"}, headers=h_owner)
    await client.post(f"{BASE}/expenses", json={
        "title": "Trigger", "amount": "5", "currency": "MAD",
        "date": "2026-05-01", "category_id": cat_id,
    }, headers=h_owner)

    notifs = (await client.get(f"{BASE}/notifications", headers=h_owner)).json()
    notif_id = notifs[0]["id"]

    resp = await client.patch(f"{BASE}/notifications/{notif_id}/read", headers=h_other)
    assert resp.status_code == 404


# ── unread_only filter ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_unread_only_filter(client: AsyncClient):
    h = await _auth(client, "unread1")
    cat_id = await _first_category_id(client, h)

    await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "1"}, headers=h)

    # Create two budget-exceeded notifications by posting two expenses
    await client.post(f"{BASE}/expenses", json={
        "title": "E1", "amount": "10", "currency": "MAD",
        "date": "2026-05-01", "category_id": cat_id,
    }, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "E2", "amount": "10", "currency": "MAD",
        "date": "2026-05-02", "category_id": cat_id,
    }, headers=h)

    notifs = (await client.get(f"{BASE}/notifications", headers=h)).json()
    assert len(notifs) >= 2

    # Mark the first one read
    await client.patch(f"{BASE}/notifications/{notifs[0]['id']}/read", headers=h)

    unread = (await client.get(f"{BASE}/notifications", params={"unread_only": True}, headers=h)).json()
    assert all(n["read_at"] is None for n in unread)
    assert len(unread) < len(notifs)
