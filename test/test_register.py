from unittest.mock import patch, MagicMock
import json
import functions.register.register as register
from utils import generate_context, generate_api_gw_event

VALID_BODY = {
    "activation_code": "ABCD1234",
    "first_name": "Alice",
    "last_name": "Smith",
    "email": "alice@example.com",
    "mobile": "+447123456789",
    "password": "SecurePass1",
    "birthday_day": 15,
    "birthday_month": 6,
    "membership_type": "individual",
}

OTHER_INVITE = {
    "id": "invite-uuid-1234",
    "relationship": "other",
    "invited_by": "admin-uuid-5678",
    "is_legacy": False,
    "date_joined": None,
}

SPOUSE_INVITE = {
    "id": "invite-uuid-1234",
    "relationship": "spouse",
    "invited_by": "admin-uuid-5678",
    "is_legacy": False,
    "date_joined": None,
}

PERIOD_ROW = {
    "id": "period-uuid-1234",
    "membership_id": "membership-uuid-1234",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "status": "active",
    "created_at": "2026-01-01T00:00:00",
}


def _make_uow(invite=OTHER_INVITE, member_id="member-uuid-1234",
              membership_id="membership-uuid-1234", inviter_membership_id="membership-uuid-5678"):
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.invites.get_by_activation_code.return_value = invite
    uow.members.insert.return_value = member_id
    uow.memberships.insert.return_value = membership_id
    uow.memberships.get_id_by_member_id.return_value = inviter_membership_id
    uow.periods.insert.return_value = PERIOD_ROW
    return uow


@patch("functions.register.register.RegisterUoW")
@patch("shared.services.register_service.sign_up", return_value=("cognito-username-123", "cognito-sub-123"))
@patch("shared.services.register_service.confirm_sign_up")
def test_register_other_returns_201(mock_confirm, mock_signup, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = register.handler(generate_api_gw_event(VALID_BODY), generate_context())
    assert result["statusCode"] == 201
    mock_signup.assert_called_once_with("+447123456789", "SecurePass1")
    mock_confirm.assert_called_once_with("cognito-username-123")


@patch("functions.register.register.RegisterUoW")
@patch("shared.services.register_service.sign_up", return_value=("cognito-username-123", "cognito-sub-123"))
@patch("shared.services.register_service.confirm_sign_up")
def test_register_spouse_returns_201(mock_confirm, mock_signup, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(invite=SPOUSE_INVITE)
    body = {**VALID_BODY}
    body.pop("membership_type")
    result = register.handler(generate_api_gw_event(body), generate_context())
    assert result["statusCode"] == 201


@patch("functions.register.register.RegisterUoW")
def test_register_invalid_activation_code_returns_404(mock_uow_cls):
    uow = _make_uow()
    uow.invites.get_by_activation_code.return_value = None
    mock_uow_cls.return_value = uow
    result = register.handler(generate_api_gw_event(VALID_BODY), generate_context())
    assert result["statusCode"] == 404


@patch("functions.register.register.RegisterUoW")
def test_register_other_without_membership_type_returns_400(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    body = {**VALID_BODY}
    body.pop("membership_type")
    result = register.handler(generate_api_gw_event(body), generate_context())
    assert result["statusCode"] == 400
    assert "membership_type" in json.loads(result["body"])["error"]


def test_register_missing_required_fields_returns_400():
    result = register.handler(generate_api_gw_event({"activation_code": "ABCD1234"}), generate_context())
    assert result["statusCode"] == 400


@patch("functions.register.register.RegisterUoW")
@patch("shared.services.register_service.sign_up", return_value=("cognito-username-123", "cognito-sub-123"))
@patch("shared.services.register_service.confirm_sign_up")
@patch("shared.services.register_service.delete_user")
def test_register_db_failure_rolls_back_cognito(mock_delete, mock_confirm, mock_signup, mock_uow_cls):
    uow = _make_uow()
    uow.members.insert.side_effect = Exception("DB insert failed")
    mock_uow_cls.return_value = uow
    result = register.handler(generate_api_gw_event(VALID_BODY), generate_context())
    assert result["statusCode"] == 500
    mock_delete.assert_called_once_with("cognito-username-123")
