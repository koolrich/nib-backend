from unittest.mock import patch, MagicMock
import functions.send_invite.send_invite as send_invite
from utils import generate_context, generate_api_gw_event

COGNITO_SUB = "test-cognito-sub-123"
MEMBER = {"id": "member-uuid-1234", "member_role": "member"}
EXEC_MEMBER = {"id": "member-uuid-1234", "member_role": "executive"}

VALID_BODY = {
    "first_name": "Alice",
    "last_name": "Smith",
    "mobile": "+447123456789",
    "relationship": "spouse",
}


def _make_uow(member=MEMBER, mobile_exists=False, pending_exists=False):
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.members.get_by_cognito_sub.return_value = member
    uow.members.mobile_exists.return_value = mobile_exists
    uow.invites.pending_exists.return_value = pending_exists
    return uow


@patch("functions.send_invite.send_invite.InviteUoW")
@patch("shared.services.invite_service.publish_invite_sms")
def test_handler_200_ok(mock_sms, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = send_invite.handler(generate_api_gw_event(VALID_BODY, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 200


@patch("functions.send_invite.send_invite.InviteUoW")
def test_handler_403_member_not_found(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(member=None)
    result = send_invite.handler(generate_api_gw_event(VALID_BODY, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 403


@patch("functions.send_invite.send_invite.InviteUoW")
def test_handler_400_missing_fields(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = send_invite.handler(generate_api_gw_event({"first_name": "Alice"}, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 400


@patch("functions.send_invite.send_invite.InviteUoW")
def test_handler_400_invalid_mobile(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = send_invite.handler(generate_api_gw_event({**VALID_BODY, "mobile": "+abc"}, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 400


@patch("functions.send_invite.send_invite.InviteUoW")
def test_handler_409_mobile_already_member(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(mobile_exists=True)
    result = send_invite.handler(generate_api_gw_event(VALID_BODY, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 409


@patch("functions.send_invite.send_invite.InviteUoW")
def test_handler_409_pending_invite_exists(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(pending_exists=True)
    result = send_invite.handler(generate_api_gw_event(VALID_BODY, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 409


@patch("functions.send_invite.send_invite.InviteUoW")
def test_handler_403_legacy_requires_executive(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(member=MEMBER)
    result = send_invite.handler(generate_api_gw_event({**VALID_BODY, "is_legacy": True}, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 403


@patch("functions.send_invite.send_invite.InviteUoW")
def test_handler_400_legacy_missing_date_joined(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(member=EXEC_MEMBER)
    result = send_invite.handler(generate_api_gw_event({**VALID_BODY, "is_legacy": True}, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 400


@patch("functions.send_invite.send_invite.InviteUoW")
@patch("shared.services.invite_service.publish_invite_sms")
def test_handler_200_legacy_allowed_for_executive(mock_sms, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(member=EXEC_MEMBER)
    result = send_invite.handler(
        generate_api_gw_event({**VALID_BODY, "is_legacy": True, "date_joined": "2020-01-01"}, cognito_sub=COGNITO_SUB),
        generate_context(),
    )
    assert result["statusCode"] == 200
