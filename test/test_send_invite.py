from unittest.mock import patch, MagicMock
import json
import uuid
import functions.send_invite.send_invite as send_invite
from utils import generate_context, generate_api_gw_event


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
def test_handler_200_Ok(mock_get_connection, mock_boto_client, mock_db, mock_sns):
    mock_get_connection.return_value = mock_db
    mock_boto_client.return_value = mock_sns

    # ---- Run function ----
    event = generate_api_gw_event(
        {
            "first_name": "Alice",
            "last_name": "Smith",
            "mobile": "+447123456789",
            "relationship": "spouse",
        }
    )

    result = send_invite.handler(event, generate_context())

    # ---- Assertions ----
    mock_get_connection.assert_called_once()
    assert result["statusCode"] == 200


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
def test_handler_400_missing_fields(
    mock_get_connection, mock_boto_client, mock_db, mock_sns
):
    mock_get_connection.return_value = mock_db
    mock_boto_client.return_value = mock_sns
    event = generate_api_gw_event({"first_name": "Alice"})

    result = send_invite.handler(event, generate_context())
    assert result["statusCode"] == 400


@patch("boto3.client")
@patch("functions.send_invite.send_invite.get_connection")
def test_handler_400_invalid_mobile(
    mock_get_connection, mock_boto_client, mock_db, mock_sns
):
    mock_get_connection.return_value = mock_db
    mock_boto_client.return_value = mock_sns
    event = generate_api_gw_event(
        {"first_name": "Alice", "last_name": "Smith", "mobile": "+abc"}
    )
    result = send_invite.handler(event, generate_context())
    assert result["statusCode"] == 400
