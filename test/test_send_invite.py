from unittest.mock import patch, MagicMock
import json
import uuid
import functions.send_invite.send_invite as send_invite
from utils import generate_context, generate_api_gw_event

COGNITO_SUB = "test-cognito-sub-123"
MEMBER_ID = "member-uuid-1234"


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_by_cognito_sub")
def test_handler_200_Ok(mock_get_member, mock_get_connection, mock_boto_client, mock_db, mock_sns):
    mock_get_connection.return_value = mock_db
    mock_boto_client.return_value = mock_sns
    mock_get_member.return_value = {"id": MEMBER_ID}

    event = generate_api_gw_event(
        {
            "first_name": "Alice",
            "last_name": "Smith",
            "mobile": "+447123456789",
            "relationship": "spouse",
        },
        cognito_sub=COGNITO_SUB,
    )

    result = send_invite.handler(event, generate_context())

    mock_get_connection.assert_called_once()
    mock_get_member.assert_called_once_with(mock_db, COGNITO_SUB)
    assert result["statusCode"] == 200


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_by_cognito_sub")
def test_handler_403_member_not_found(mock_get_member, mock_get_connection, mock_boto_client, mock_db, mock_sns):
    mock_get_connection.return_value = mock_db
    mock_boto_client.return_value = mock_sns
    mock_get_member.return_value = None

    event = generate_api_gw_event(
        {
            "first_name": "Alice",
            "last_name": "Smith",
            "mobile": "+447123456789",
            "relationship": "spouse",
        },
        cognito_sub=COGNITO_SUB,
    )

    result = send_invite.handler(event, generate_context())
    assert result["statusCode"] == 403


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_by_cognito_sub")
def test_handler_400_missing_fields(mock_get_member, mock_get_connection, mock_boto_client, mock_db, mock_sns):
    mock_get_connection.return_value = mock_db
    mock_boto_client.return_value = mock_sns
    mock_get_member.return_value = {"id": MEMBER_ID}

    event = generate_api_gw_event({"first_name": "Alice"}, cognito_sub=COGNITO_SUB)

    result = send_invite.handler(event, generate_context())
    assert result["statusCode"] == 400


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
@patch("functions.send_invite.send_invite.get_member_by_cognito_sub")
def test_handler_400_invalid_mobile(mock_get_member, mock_get_connection, mock_boto_client, mock_db, mock_sns):
    mock_get_connection.return_value = mock_db
    mock_boto_client.return_value = mock_sns
    mock_get_member.return_value = {"id": MEMBER_ID}

    event = generate_api_gw_event(
        {"first_name": "Alice", "last_name": "Smith", "mobile": "+abc"},
        cognito_sub=COGNITO_SUB,
    )
    result = send_invite.handler(event, generate_context())
    assert result["statusCode"] == 400
