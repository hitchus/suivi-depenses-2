from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

BASE = "/api/v1"


async def _auth(client: AsyncClient, suffix: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={
        "email": f"rec{suffix}@test.com",
        "password": "password123",
        "display_name": f"Rec {suffix}",
    })
    resp = await client.post(f"{BASE}/auth/login", json={
        "email": f"rec{suffix}@test.com", "password": "password123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def _first_category_id(client: AsyncClient, headers: dict) -> str:
    cats = (await client.get(f"{BASE}/categories", headers=headers)).json()
    return cats[0]["id"]


# ── CRUD ──────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_recurring_rule(client: AsyncClient):
    h = await _auth(client, "create1")
    cat_id = await _first_category_id(client, h)

    resp = await client.post(f"{BASE}/recurring", json={
        "title": "Loyer", "amount": "3000", "currency": "MAD",
        "category_id": cat_id, "frequency": "monthly",
        "start_date": "2026-05-01",
    }, headers=h)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Loyer"
    assert body["frequency"] == "monthly"
    assert body["active"] is True
    assert "2026-05-01" in body["next_run"]


@pytest.mark.asyncio
async def test_list_recurring_rules(client: AsyncClient):
    h = await _auth(client, "list1")
    cat_id = await _first_category_id(client, h)

    await client.post(f"{BASE}/recurring", json={
        "title": "Internet", "amount": "200", "currency": "MAD",
        "frequency": "monthly", "start_date": "2026-05-01",
    }, headers=h)
    await client.post(f"{BASE}/recurring", json={
        "title": "Netflix", "amount": "80", "currency": "MAD",
        "category_id": cat_id, "frequency": "monthly", "start_date": "2026-05-15",
    }, headers=h)

    rules = (await client.get(f"{BASE}/recurring", headers=h)).json()
    assert len(rules) == 2


@pytest.mark.asyncio
async def test_deactivate_rule(client: AsyncClient):
    h = await _auth(client, "del1")

    rule = (await client.post(f"{BASE}/recurring", json={
        "title": "Gym", "amount": "250", "currency": "MAD",
        "frequency": "monthly", "start_date": "2026-05-01",
    }, headers=h)).json()

    resp = await client.delete(f"{BASE}/recurring/{rule['id']}", headers=h)
    assert resp.status_code == 200
    assert resp.json()["active"] is False

    # No longer appears in active list
    rules = (await client.get(f"{BASE}/recurring", headers=h)).json()
    assert not any(r["id"] == rule["id"] for r in rules)


@pytest.mark.asyncio
async def test_deactivate_other_user_rule_returns_404(client: AsyncClient):
    h1 = await _auth(client, "own1")
    h2 = await _auth(client, "own2")

    rule = (await client.post(f"{BASE}/recurring", json={
        "title": "Private", "amount": "100", "currency": "MAD",
        "frequency": "weekly", "start_date": "2026-05-01",
    }, headers=h1)).json()

    resp = await client.delete(f"{BASE}/recurring/{rule['id']}", headers=h2)
    assert resp.status_code == 404


# ── next_occurrence helper ────────────────────────────────────────────────────

def test_next_occurrence_weekly():
    from app.services.recurring_service import _next_occurrence
    d = date(2026, 5, 1)
    nxt = _next_occurrence("weekly", d)
    assert nxt.date() == date(2026, 5, 8)


def test_next_occurrence_monthly():
    from app.services.recurring_service import _next_occurrence
    d = date(2026, 5, 31)
    nxt = _next_occurrence("monthly", d)
    assert nxt.date() == date(2026, 6, 30)  # June has only 30 days


def test_next_occurrence_monthly_year_wrap():
    from app.services.recurring_service import _next_occurrence
    d = date(2026, 12, 15)
    nxt = _next_occurrence("monthly", d)
    assert nxt.date() == date(2027, 1, 15)


def test_next_occurrence_yearly():
    from app.services.recurring_service import _next_occurrence
    d = date(2024, 2, 29)  # leap day
    nxt = _next_occurrence("yearly", d)
    assert nxt.date() == date(2025, 2, 28)  # 2025 is not a leap year


# ── Scheduler job (direct invocation) ────────────────────────────────────────

@pytest.mark.asyncio
async def test_process_due_rules_creates_expense(client: AsyncClient, db_session: AsyncSession):
    from app.services.recurring_service import process_due_rules

    h = await _auth(client, "proc1")

    # start_date in the past → rule is already due
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    rule = (await client.post(f"{BASE}/recurring", json={
        "title": "Eau", "amount": "150", "currency": "MAD",
        "frequency": "monthly", "start_date": yesterday,
    }, headers=h)).json()

    count = await process_due_rules(db_session)
    assert count >= 1

    # Expense should now exist
    expenses = (await client.get(f"{BASE}/expenses", headers=h)).json()
    assert any(e["title"] == "Eau" for e in expenses)


@pytest.mark.asyncio
async def test_process_due_rules_advances_next_run(client: AsyncClient, db_session: AsyncSession):
    from sqlalchemy import select
    from app.models.recurring_rule import RecurringRule
    from app.services.recurring_service import process_due_rules

    h = await _auth(client, "proc2")

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    rule_resp = (await client.post(f"{BASE}/recurring", json={
        "title": "Électricité", "amount": "300", "currency": "MAD",
        "frequency": "monthly", "start_date": yesterday,
    }, headers=h)).json()

    await process_due_rules(db_session)

    # Reload rule from DB
    import uuid
    rule_in_db = (await db_session.execute(
        select(RecurringRule).where(RecurringRule.id == uuid.UUID(rule_resp["id"]))
    )).scalar_one()
    # next_run should be ~1 month ahead, definitely past yesterday
    assert rule_in_db.next_run.date() > date.today()


@pytest.mark.asyncio
async def test_process_skips_future_rules(client: AsyncClient, db_session: AsyncSession):
    from app.services.recurring_service import process_due_rules

    h = await _auth(client, "proc3")

    # start_date in the future
    future = (date.today() + timedelta(days=10)).isoformat()
    await client.post(f"{BASE}/recurring", json={
        "title": "Future expense", "amount": "500", "currency": "MAD",
        "frequency": "monthly", "start_date": future,
    }, headers=h)

    count_before = len((await client.get(f"{BASE}/expenses", headers=h)).json())
    await process_due_rules(db_session)
    count_after = len((await client.get(f"{BASE}/expenses", headers=h)).json())

    assert count_after == count_before  # nothing created


@pytest.mark.asyncio
async def test_process_skips_inactive_rules(client: AsyncClient, db_session: AsyncSession):
    from app.services.recurring_service import process_due_rules

    h = await _auth(client, "proc4")

    yesterday = (date.today() - timedelta(days=1)).isoformat()
    rule = (await client.post(f"{BASE}/recurring", json={
        "title": "Cancelled", "amount": "100", "currency": "MAD",
        "frequency": "monthly", "start_date": yesterday,
    }, headers=h)).json()

    # Deactivate before processing
    await client.delete(f"{BASE}/recurring/{rule['id']}", headers=h)

    count_before = len((await client.get(f"{BASE}/expenses", headers=h)).json())
    await process_due_rules(db_session)
    count_after = len((await client.get(f"{BASE}/expenses", headers=h)).json())

    assert count_after == count_before
