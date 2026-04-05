from unittest.mock import patch
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


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_context", return_value=MEMBER)
@patch("functions.send_invite.send_invite.mobile_is_member", return_value=False)
@patch("functions.send_invite.send_invite.pending_invite_exists", return_value=False)
def test_handler_200_ok(mock_pending, mock_is_member, mock_ctx, mock_conn, mock_boto, mock_db, mock_sns):
    mock_conn.return_value = mock_db
    mock_boto.return_value = mock_sns
    result = send_invite.handler(generate_api_gw_event(VALID_BODY, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 200


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_context", return_value=None)
def test_handler_403_member_not_found(mock_ctx, mock_conn, mock_boto, mock_db, mock_sns):
    mock_conn.return_value = mock_db
    mock_boto.return_value = mock_sns
    result = send_invite.handler(generate_api_gw_event(VALID_BODY, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 403


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_context", return_value=MEMBER)
def test_handler_400_missing_fields(mock_ctx, mock_conn, mock_boto, mock_db, mock_sns):
    mock_conn.return_value = mock_db
    mock_boto.return_value = mock_sns
    result = send_invite.handler(generate_api_gw_event({"first_name": "Alice"}, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 400


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_context", return_value=MEMBER)
def test_handler_400_invalid_mobile(mock_ctx, mock_conn, mock_boto, mock_db, mock_sns):
    mock_conn.return_value = mock_db
    mock_boto.return_value = mock_sns
    result = send_invite.handler(generate_api_gw_event({**VALID_BODY, "mobile": "+abc"}, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 400


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_context", return_value=MEMBER)
@patch("functions.send_invite.send_invite.mobile_is_member", return_value=True)
def test_handler_409_mobile_already_member(mock_is_member, mock_ctx, mock_conn, mock_boto, mock_db, mock_sns):
    mock_conn.return_value = mock_db
    mock_boto.return_value = mock_sns
    result = send_invite.handler(generate_api_gw_event(VALID_BODY, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 409


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_context", return_value=MEMBER)
@patch("functions.send_invite.send_invite.mobile_is_member", return_value=False)
@patch("functions.send_invite.send_invite.pending_invite_exists", return_value=True)
def test_handler_409_pending_invite_exists(mock_pending, mock_is_member, mock_ctx, mock_conn, mock_boto, mock_db, mock_sns):
    mock_conn.return_value = mock_db
    mock_boto.return_value = mock_sns
    result = send_invite.handler(generate_api_gw_event(VALID_BODY, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 409


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_context", return_value=MEMBER)
@patch("functions.send_invite.send_invite.mobile_is_member", return_value=False)
@patch("functions.send_invite.send_invite.pending_invite_exists", return_value=False)
def test_handler_403_legacy_requires_executive(mock_pending, mock_is_member, mock_ctx, mock_conn, mock_boto, mock_db, mock_sns):
    mock_conn.return_value = mock_db
    mock_boto.return_value = mock_sns
    result = send_invite.handler(generate_api_gw_event({**VALID_BODY, "is_legacy": True}, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 403


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.send_invite.send_invite.mobile_is_member", return_value=False)
@patch("functions.send_invite.send_invite.pending_invite_exists", return_value=False)
def test_handler_200_legacy_allowed_for_executive(mock_pending, mock_is_member, mock_ctx, mock_conn, mock_boto, mock_db, mock_sns):
    mock_conn.return_value = mock_db
    mock_boto.return_value = mock_sns
    result = send_invite.handler(generate_api_gw_event({**VALID_BODY, "is_legacy": True}, cognito_sub=COGNITO_SUB), generate_context())
    assert result["statusCode"] == 200
