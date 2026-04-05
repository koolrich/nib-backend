import json
from unittest.mock import patch
import functions.members.members as members
from utils import generate_context, generate_api_gw_event

MEMBER = {"id": "member-uuid", "member_role": "member"}
EXEC_MEMBER = {"id": "exec-uuid", "member_role": "executive"}

MEMBER_PROFILE = {
    "id": "member-uuid", "first_name": "Alice", "last_name": "Smith",
    "email": "alice@example.com", "mobile": "+447123456789",
    "address_line1": None, "address_line2": None, "town": None, "post_code": None,
    "state_of_origin": None, "lga": None, "birthday_day": 1, "birthday_month": 6,
    "relationship_status": None, "emergency_contact_name": None,
    "emergency_contact_phone": None, "member_role": "member",
    "status": "active", "updated_at": "2026-04-05T10:00:00",
}

MY_PLEDGE = {
    "id": "pledge-uuid", "event_id": "event-uuid",
    "event_title": "August Meeting", "event_date": "2026-08-12",
    "item_name": "Crates of Coke", "unit": "crates",
    "quantity": 5, "status": "pledged",
    "created_at": "2026-04-05T10:00:00",
    "contribution_amount": None, "contribution_received_at": None,
}

MY_PLEDGE_WITH_CONTRIBUTION = {
    **MY_PLEDGE,
    "contribution_amount": 50.00,
    "contribution_received_at": "2026-04-05T12:00:00",
}


def _event(route_key, body=None, path_params=None, cognito_sub="member-sub"):
    ev = generate_api_gw_event(body, cognito_sub=cognito_sub)
    ev["routeKey"] = route_key
    if path_params:
        ev["pathParameters"] = path_params
    return ev


@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=MEMBER)
@patch("functions.members.members.get_member_pledges", return_value=[MY_PLEDGE])
def test_get_my_pledges_returns_200(mock_pledges, mock_ctx, mock_conn):
    result = members.handler(_event("GET /members/me/pledges"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["pledges"]) == 1
    assert body["pledges"][0]["contribution"] is None


@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=MEMBER)
@patch("functions.members.members.get_member_pledges", return_value=[MY_PLEDGE_WITH_CONTRIBUTION])
def test_get_my_pledges_includes_contribution(mock_pledges, mock_ctx, mock_conn):
    result = members.handler(_event("GET /members/me/pledges"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["pledges"][0]["contribution"]["amount"] == 50.00


@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=MEMBER)
@patch("functions.members.members.get_member_pledges", return_value=[])
def test_get_my_pledges_empty(mock_pledges, mock_ctx, mock_conn):
    result = members.handler(_event("GET /members/me/pledges"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["pledges"] == []


@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=None)
def test_member_not_found_returns_403(mock_ctx, mock_conn):
    result = members.handler(_event("GET /members/me/pledges"), generate_context())
    assert result["statusCode"] == 403


# ── PATCH /members/{id} ───────────────────────────────────────────────────────

@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=MEMBER)
@patch("functions.members.members.get_member_by_id", return_value=MEMBER_PROFILE)
@patch("functions.members.members.update_member", return_value=MEMBER_PROFILE)
def test_patch_own_profile_returns_200(mock_update, mock_get, mock_ctx, mock_conn):
    result = members.handler(_event("PATCH /members/{id}", {"first_name": "Alicia"}, {"id": "member-uuid"}), generate_context())
    assert result["statusCode"] == 200


@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=MEMBER)
def test_patch_other_member_returns_403(mock_ctx, mock_conn):
    result = members.handler(_event("PATCH /members/{id}", {"first_name": "Bob"}, {"id": "other-uuid"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.members.members.get_member_by_id", return_value=MEMBER_PROFILE)
@patch("functions.members.members.update_member", return_value=MEMBER_PROFILE)
def test_exec_can_patch_any_member(mock_update, mock_get, mock_ctx, mock_conn):
    result = members.handler(_event("PATCH /members/{id}", {"first_name": "Bob"}, {"id": "member-uuid"}, cognito_sub="exec-sub"), generate_context())
    assert result["statusCode"] == 200


@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=MEMBER)
@patch("functions.members.members.get_member_by_id", return_value=MEMBER_PROFILE)
def test_patch_role_by_regular_member_returns_403(mock_get, mock_ctx, mock_conn):
    result = members.handler(_event("PATCH /members/{id}", {"member_role": "executive"}, {"id": "member-uuid"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.members.members.get_connection")
@patch("functions.members.members.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.members.members.get_member_by_id", return_value=None)
def test_patch_nonexistent_member_returns_404(mock_get, mock_ctx, mock_conn):
    result = members.handler(_event("PATCH /members/{id}", {"first_name": "Bob"}, {"id": "bad-uuid"}, cognito_sub="exec-sub"), generate_context())
    assert result["statusCode"] == 404
