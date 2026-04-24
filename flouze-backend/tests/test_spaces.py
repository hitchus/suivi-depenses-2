import pytest
from httpx import AsyncClient

BASE = "/api/v1"


async def _auth(client: AsyncClient, suffix: str) -> dict:
    await client.post(f"{BASE}/auth/register", json={
        "email": f"sp{suffix}@test.com",
        "password": "password123",
        "display_name": f"Sp {suffix}",
    })
    resp = await client.post(f"{BASE}/auth/login", json={
        "email": f"sp{suffix}@test.com", "password": "password123",
    })
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ── Create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_space(client: AsyncClient):
    h = await _auth(client, "create1")
    resp = await client.post(f"{BASE}/spaces", json={"name": "Couple"}, headers=h)
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Couple"
    assert "id" in body


@pytest.mark.asyncio
async def test_creator_appears_in_user_spaces(client: AsyncClient):
    h = await _auth(client, "creator1")
    space = (await client.post(f"{BASE}/spaces", json={"name": "Work"}, headers=h)).json()
    spaces = (await client.get(f"{BASE}/spaces", headers=h)).json()
    assert any(s["id"] == space["id"] for s in spaces)


# ── Invite ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_invite_existing_user(client: AsyncClient):
    h_owner = await _auth(client, "inv_owner1")
    await _auth(client, "inv_member1")  # register member

    space = (await client.post(f"{BASE}/spaces", json={"name": "Famille"}, headers=h_owner)).json()
    resp = await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "spinv_member1@test.com"},
        headers=h_owner,
    )
    assert resp.status_code == 201
    assert resp.json()["role"] == "member"


@pytest.mark.asyncio
async def test_invited_member_sees_space(client: AsyncClient):
    h_owner = await _auth(client, "see_owner1")
    h_member = await _auth(client, "see_member1")

    space = (await client.post(f"{BASE}/spaces", json={"name": "Shared"}, headers=h_owner)).json()
    await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "spsee_member1@test.com"},
        headers=h_owner,
    )

    spaces_of_member = (await client.get(f"{BASE}/spaces", headers=h_member)).json()
    assert any(s["id"] == space["id"] for s in spaces_of_member)


@pytest.mark.asyncio
async def test_invite_nonexistent_email_returns_404(client: AsyncClient):
    h = await _auth(client, "inv404_1")
    space = (await client.post(f"{BASE}/spaces", json={"name": "X"}, headers=h)).json()
    resp = await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "nobody_xyz_abc@test.com"},
        headers=h,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_invite_already_member_returns_409(client: AsyncClient):
    h_owner = await _auth(client, "dup_owner1")
    await _auth(client, "dup_member1")

    space = (await client.post(f"{BASE}/spaces", json={"name": "Y"}, headers=h_owner)).json()
    await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "spdup_member1@test.com"},
        headers=h_owner,
    )
    resp = await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "spdup_member1@test.com"},
        headers=h_owner,
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_non_admin_cannot_invite(client: AsyncClient):
    h_owner = await _auth(client, "perm_owner1")
    h_member = await _auth(client, "perm_member1")
    await _auth(client, "perm_other1")

    space = (await client.post(f"{BASE}/spaces", json={"name": "Z"}, headers=h_owner)).json()
    await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "spperm_member1@test.com"},
        headers=h_owner,
    )

    # member (not admin) tries to invite someone else
    resp = await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "spperm_other1@test.com"},
        headers=h_member,
    )
    assert resp.status_code == 403


# ── Shared expenses visibility ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_shared_expense_visible_to_member(client: AsyncClient):
    h_owner = await _auth(client, "vis_owner1")
    h_member = await _auth(client, "vis_member1")

    space = (await client.post(f"{BASE}/spaces", json={"name": "Casa"}, headers=h_owner)).json()
    await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "spvis_member1@test.com"},
        headers=h_owner,
    )

    exp = (await client.post(f"{BASE}/expenses", json={
        "title": "Loyer partagé", "amount": "5000", "currency": "MAD",
        "date": "2026-05-01", "space_id": space["id"],
    }, headers=h_owner)).json()

    expenses_of_member = (await client.get(f"{BASE}/expenses", headers=h_member)).json()
    assert any(e["id"] == exp["id"] for e in expenses_of_member)


@pytest.mark.asyncio
async def test_shared_expense_not_visible_to_outsider(client: AsyncClient):
    h_owner = await _auth(client, "out_owner1")
    h_outsider = await _auth(client, "out_other1")

    space = (await client.post(f"{BASE}/spaces", json={"name": "Private"}, headers=h_owner)).json()
    exp = (await client.post(f"{BASE}/expenses", json={
        "title": "Secret", "amount": "100", "currency": "MAD",
        "date": "2026-05-01", "space_id": space["id"],
    }, headers=h_owner)).json()

    expenses_of_outsider = (await client.get(f"{BASE}/expenses", headers=h_outsider)).json()
    assert exp["id"] not in {e["id"] for e in expenses_of_outsider}


# ── Role management ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_promote_member_to_admin(client: AsyncClient):
    h_owner = await _auth(client, "role_owner1")
    h_member = await _auth(client, "role_member1")

    space = (await client.post(f"{BASE}/spaces", json={"name": "Team"}, headers=h_owner)).json()
    member_rec = (await client.post(
        f"{BASE}/spaces/{space['id']}/invite",
        json={"email": "sprole_member1@test.com"},
        headers=h_owner,
    )).json()

    resp = await client.patch(
        f"{BASE}/spaces/{space['id']}/members/{member_rec['user_id']}",
        json={"role": "admin"},
        headers=h_owner,
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"
