import pytest
from httpx import AsyncClient

BASE = "/api/v1"
MONTH = "2026-05"


async def _auth(client: AsyncClient, suffix: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={
        "email": f"dash{suffix}@test.com",
        "password": "password123",
        "display_name": f"Dash {suffix}",
    })
    resp = await client.post(f"{BASE}/auth/login", json={
        "email": f"dash{suffix}@test.com", "password": "password123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _first_category_id(client: AsyncClient, headers: dict) -> str:
    cats = (await client.get(f"{BASE}/categories", headers=headers)).json()
    return cats[0]["id"]


# ── Dashboard structure ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_empty_dashboard_returns_zeroes(client: AsyncClient):
    h = await _auth(client, "empty1")
    resp = await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == "0"
    assert body["budget_global"] is None
    assert body["restant"] is None
    assert isinstance(body["by_category"], list)
    assert len(body["by_category"]) > 0  # seeded categories present


@pytest.mark.asyncio
async def test_dashboard_aggregates_expenses(client: AsyncClient):
    h = await _auth(client, "agg1")
    cat_id = await _first_category_id(client, h)

    await client.post(f"{BASE}/expenses", json={
        "title": "Courses A", "amount": "200", "currency": "MAD",
        "date": "2026-05-10", "category_id": cat_id,
    }, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "Courses B", "amount": "300", "currency": "MAD",
        "date": "2026-05-15", "category_id": cat_id,
    }, headers=h)

    body = (await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)).json()
    assert float(body["total"]) == pytest.approx(500, abs=1)


@pytest.mark.asyncio
async def test_dashboard_different_month_excluded(client: AsyncClient):
    h = await _auth(client, "excl1")
    cat_id = await _first_category_id(client, h)

    await client.post(f"{BASE}/expenses", json={
        "title": "April expense", "amount": "999", "currency": "MAD",
        "date": "2026-04-20", "category_id": cat_id,
    }, headers=h)

    body = (await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)).json()
    assert float(body["total"]) == pytest.approx(0, abs=1)


# ── Global budget / restant ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_global_budget_restant(client: AsyncClient):
    h = await _auth(client, "budget1")
    cat_id = await _first_category_id(client, h)

    await client.put(f"{BASE}/budgets/global", json={"month": MONTH, "amount": "1000"}, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "Loyer", "amount": "600", "currency": "MAD",
        "date": "2026-05-01", "category_id": cat_id,
    }, headers=h)

    body = (await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)).json()
    assert float(body["budget_global"]) == pytest.approx(1000, abs=1)
    assert float(body["restant"]) == pytest.approx(400, abs=1)


# ── Redis cache ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_dashboard_cache_set_after_first_call(client: AsyncClient, fake_redis_setup):
    h = await _auth(client, "cache1")

    login_resp = await client.post(f"{BASE}/auth/login", json={
        "email": "dashcache1@test.com", "password": "password123",
    })
    user_id = login_resp.json().get("user_id") or login_resp.json().get("id")

    await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)

    keys = await fake_redis_setup.keys("dash:*")
    assert any(MONTH in k for k in keys)


@pytest.mark.asyncio
async def test_dashboard_cache_invalidated_after_expense(client: AsyncClient, fake_redis_setup):
    h = await _auth(client, "cache2")
    cat_id = await _first_category_id(client, h)

    # Populate cache
    await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)
    keys_before = await fake_redis_setup.keys("dash:*:2026-05")
    # A key must exist for this user
    assert len(keys_before) >= 1

    # Adding an expense should invalidate the cache
    await client.post(f"{BASE}/expenses", json={
        "title": "Post-cache expense", "amount": "50", "currency": "MAD",
        "date": "2026-05-20", "category_id": cat_id,
    }, headers=h)

    # Re-fetch: fresh data should be returned (and no stale cache)
    body = (await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)).json()
    assert float(body["total"]) >= 50


# ── Monthly trend ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_monthly_trend_has_six_entries(client: AsyncClient):
    h = await _auth(client, "trend1")
    body = (await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)).json()
    assert len(body["monthly_trend"]) == 6


@pytest.mark.asyncio
async def test_monthly_trend_ends_at_requested_month(client: AsyncClient):
    h = await _auth(client, "trend2")
    body = (await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)).json()
    assert body["monthly_trend"][-1]["month"] == MONTH


@pytest.mark.asyncio
async def test_monthly_trend_counts_expenses_in_correct_months(client: AsyncClient):
    h = await _auth(client, "trend3")
    cat_id = await _first_category_id(client, h)

    await client.post(f"{BASE}/expenses", json={
        "title": "May", "amount": "100", "currency": "MAD",
        "date": "2026-05-05", "category_id": cat_id,
    }, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "March", "amount": "200", "currency": "MAD",
        "date": "2026-03-10", "category_id": cat_id,
    }, headers=h)

    body = (await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)).json()
    trend = {pt["month"]: float(pt["total"]) for pt in body["monthly_trend"]}
    assert trend.get("2026-05", 0) == pytest.approx(100, abs=1)
    assert trend.get("2026-03", 0) == pytest.approx(200, abs=1)


# ── Budget CRUD ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upsert_global_budget(client: AsyncClient):
    h = await _auth(client, "bud_glob1")
    resp = await client.put(f"{BASE}/budgets/global", json={"month": MONTH, "amount": "2000"}, headers=h)
    assert resp.status_code == 200
    assert float(resp.json()["amount"]) == pytest.approx(2000, abs=1)


@pytest.mark.asyncio
async def test_upsert_global_budget_updates_existing(client: AsyncClient):
    h = await _auth(client, "bud_upd1")
    await client.put(f"{BASE}/budgets/global", json={"month": MONTH, "amount": "500"}, headers=h)
    resp = await client.put(f"{BASE}/budgets/global", json={"month": MONTH, "amount": "750"}, headers=h)
    assert resp.status_code == 200
    assert float(resp.json()["amount"]) == pytest.approx(750, abs=1)

    # Only one budget row should exist
    budgets = (await client.get(f"{BASE}/budgets", params={"month": MONTH}, headers=h)).json()
    global_budgets = [b for b in budgets if b["category_id"] is None]
    assert len(global_budgets) == 1


@pytest.mark.asyncio
async def test_upsert_category_budget(client: AsyncClient):
    h = await _auth(client, "bud_cat1")
    cat_id = await _first_category_id(client, h)

    resp = await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "300"}, headers=h)
    assert resp.status_code == 200
    assert resp.json()["category_id"] == cat_id
    assert float(resp.json()["amount"]) == pytest.approx(300, abs=1)


# ── by_category ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_by_category_shows_correct_spent_and_budget(client: AsyncClient):
    h = await _auth(client, "bycat1")
    cat_id = await _first_category_id(client, h)

    await client.put(f"{BASE}/budgets/{cat_id}", json={"month": MONTH, "amount": "500"}, headers=h)
    await client.post(f"{BASE}/expenses", json={
        "title": "Item", "amount": "150", "currency": "MAD",
        "date": "2026-05-07", "category_id": cat_id,
    }, headers=h)

    body = (await client.get(f"{BASE}/dashboard", params={"month": MONTH}, headers=h)).json()
    cat_progress = next((c for c in body["by_category"] if c["category_id"] == cat_id), None)
    assert cat_progress is not None
    assert float(cat_progress["spent"]) == pytest.approx(150, abs=1)
    assert float(cat_progress["budget"]) == pytest.approx(500, abs=1)
    assert cat_progress["expense_count"] == 1
