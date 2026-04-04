import json
from unittest.mock import patch
import functions.members.members as members
from utils import generate_context, generate_api_gw_event

MEMBER = {"id": "member-uuid", "member_role": "member"}

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


def _event(route_key, cognito_sub="member-sub"):
    ev = generate_api_gw_event(None, cognito_sub=cognito_sub)
    ev["routeKey"] = route_key
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
