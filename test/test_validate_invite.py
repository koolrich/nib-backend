from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
import json
import functions.validate_invite.validate_invite as validate_invite
from utils import generate_context, generate_api_gw_event


def make_invite(status="pending", expires_at=None):
    return {
        "id": "invite-uuid-1234",
        "status": status,
        "relationship": "other",
        "mobile": "+447123456789",
        "first_name": "Alice",
        "last_name": "Smith",
        "expires_at": expires_at if expires_at is not None else datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=30),
    }


def _make_uow(invite=None):
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.invites.get_by_activation_code.return_value = invite if invite is not None else make_invite()
    return uow


@patch("functions.validate_invite.validate_invite.InviteUoW")
def test_valid_invite_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = validate_invite.handler(generate_api_gw_event({"activation_code": "ABCD1234"}), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["relationship"] == "other"
    assert body["mobile"] == "+447123456789"
    assert body["first_name"] == "Alice"
    assert body["last_name"] == "Smith"


@patch("functions.validate_invite.validate_invite.InviteUoW")
def test_invalid_code_returns_404(mock_uow_cls):
    uow = _make_uow()
    uow.invites.get_by_activation_code.return_value = None
    mock_uow_cls.return_value = uow
    result = validate_invite.handler(generate_api_gw_event({"activation_code": "INVALID"}), generate_context())
    assert result["statusCode"] == 404


@patch("functions.validate_invite.validate_invite.InviteUoW")
def test_used_invite_returns_400(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(make_invite(status="used"))
    result = validate_invite.handler(generate_api_gw_event({"activation_code": "ABCD1234"}), generate_context())
    assert result["statusCode"] == 400
    assert "already been used" in json.loads(result["body"])["error"]


@patch("functions.validate_invite.validate_invite.InviteUoW")
def test_expired_status_returns_400(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(make_invite(status="expired"))
    result = validate_invite.handler(generate_api_gw_event({"activation_code": "ABCD1234"}), generate_context())
    assert result["statusCode"] == 400
    assert "expired" in json.loads(result["body"])["error"]


@patch("functions.validate_invite.validate_invite.InviteUoW")
def test_past_expiry_date_marks_expired_and_returns_400(mock_uow_cls):
    uow = _make_uow(make_invite(expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)))
    mock_uow_cls.return_value = uow
    result = validate_invite.handler(generate_api_gw_event({"activation_code": "ABCD1234"}), generate_context())
    assert result["statusCode"] == 400
    assert "expired" in json.loads(result["body"])["error"]
    uow.invites.mark_expired.assert_called_once()


def test_missing_activation_code_returns_400():
    result = validate_invite.handler(generate_api_gw_event({}), generate_context())
    assert result["statusCode"] == 400
