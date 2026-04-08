import json
from unittest.mock import patch, MagicMock
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
    "status": "active", "is_legacy": False, "date_joined": "2025-01-01",
    "membership_type": "individual",
    "created_at": "2025-01-01T10:00:00", "updated_at": "2026-04-05T10:00:00",
}

MEMBER_LIST_ITEM = {
    "id": "member-uuid", "first_name": "Alice", "last_name": "Smith",
    "member_role": "member", "date_joined": "2025-01-01",
    "membership_type": "individual", "payment_status": "pending",
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


def _make_uow(caller=MEMBER, pledges=None, member_profile=MEMBER_PROFILE, update_result=MEMBER_PROFILE, member_list=None):
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.members.get_by_cognito_sub.return_value = caller
    uow.members.get_by_id.return_value = member_profile
    uow.members.update.return_value = update_result
    uow.members.get_all.return_value = member_list if member_list is not None else [MEMBER_LIST_ITEM]
    uow.pledges.get_by_member.return_value = pledges if pledges is not None else []
    return uow


def _event(route_key, body=None, path_params=None, cognito_sub="member-sub"):
    ev = generate_api_gw_event(body, cognito_sub=cognito_sub, route_key=route_key,
                               path_params=path_params)
    return ev


@patch("functions.members.members.MemberUoW")
def test_get_my_profile_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = members.handler(_event("GET /v1/members/me"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["id"] == "member-uuid"
    assert body["member_role"] == "member"


@patch("functions.members.members.MemberUoW")
def test_get_my_pledges_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(pledges=[MY_PLEDGE])
    result = members.handler(_event("GET /v1/members/me/pledges"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["pledges"]) == 1
    assert body["pledges"][0]["contribution"] is None


@patch("functions.members.members.MemberUoW")
def test_get_my_pledges_includes_contribution(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(pledges=[MY_PLEDGE_WITH_CONTRIBUTION])
    result = members.handler(_event("GET /v1/members/me/pledges"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["pledges"][0]["contribution"]["amount"] == 50.00


@patch("functions.members.members.MemberUoW")
def test_get_my_pledges_empty(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(pledges=[])
    result = members.handler(_event("GET /v1/members/me/pledges"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["pledges"] == []


@patch("functions.members.members.MemberUoW")
def test_member_not_found_returns_403(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=None)
    result = members.handler(_event("GET /v1/members/me/pledges"), generate_context())
    assert result["statusCode"] == 403


@patch("functions.members.members.MemberUoW")
def test_patch_own_profile_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = members.handler(_event("PATCH /v1/members/{id}", {"first_name": "Alicia"}, {"id": "member-uuid"}), generate_context())
    assert result["statusCode"] == 200


@patch("functions.members.members.MemberUoW")
def test_patch_other_member_returns_403(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = members.handler(_event("PATCH /v1/members/{id}", {"first_name": "Bob"}, {"id": "other-uuid"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.members.members.MemberUoW")
def test_exec_can_patch_any_member(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=EXEC_MEMBER)
    result = members.handler(_event("PATCH /v1/members/{id}", {"first_name": "Bob"}, {"id": "member-uuid"}, cognito_sub="exec-sub"), generate_context())
    assert result["statusCode"] == 200


@patch("functions.members.members.MemberUoW")
def test_patch_role_by_regular_member_returns_403(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = members.handler(_event("PATCH /v1/members/{id}", {"member_role": "executive"}, {"id": "member-uuid"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.members.members.MemberUoW")
def test_patch_nonexistent_member_returns_404(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=EXEC_MEMBER, member_profile=None)
    result = members.handler(_event("PATCH /v1/members/{id}", {"first_name": "Bob"}, {"id": "bad-uuid"}, cognito_sub="exec-sub"), generate_context())
    assert result["statusCode"] == 404


@patch("functions.members.members.MemberUoW")
def test_get_member_by_id_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = members.handler(_event("GET /v1/members/{id}", path_params={"id": "member-uuid"}), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["id"] == "member-uuid"
    assert body["membership_type"] == "individual"
    assert body["is_legacy"] is False


@patch("functions.members.members.MemberUoW")
def test_get_member_by_id_not_found_returns_404(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(member_profile=None)
    result = members.handler(_event("GET /v1/members/{id}", path_params={"id": "bad-uuid"}), generate_context())
    assert result["statusCode"] == 404


@patch("functions.members.members.MemberUoW")
def test_list_members_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = members.handler(_event("GET /v1/members"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["members"]) == 1
    assert body["members"][0]["id"] == "member-uuid"
    assert "payment_status" not in body["members"][0]


@patch("functions.members.members.MemberUoW")
def test_list_members_exec_sees_payment_status(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=EXEC_MEMBER)
    result = members.handler(_event("GET /v1/members", cognito_sub="exec-sub"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "payment_status" in body["members"][0]
