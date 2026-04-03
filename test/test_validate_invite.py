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


@patch("functions.validate_invite.validate_invite.get_connection")
def test_valid_invite_returns_200(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    mock_db.cursor.return_value.__enter__ = lambda s: mock_db.cursor.return_value
    mock_db.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.cursor.return_value.fetchone.return_value = make_invite()

    event = generate_api_gw_event({"activation_code": "ABCD1234"})
    result = validate_invite.handler(event, generate_context())

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["relationship"] == "other"
    assert body["mobile"] == "+447123456789"
    assert body["first_name"] == "Alice"
    assert body["last_name"] == "Smith"


@patch("functions.validate_invite.validate_invite.get_connection")
def test_invalid_code_returns_404(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    mock_db.cursor.return_value.__enter__ = lambda s: mock_db.cursor.return_value
    mock_db.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.cursor.return_value.fetchone.return_value = None

    event = generate_api_gw_event({"activation_code": "INVALID"})
    result = validate_invite.handler(event, generate_context())

    assert result["statusCode"] == 404


@patch("functions.validate_invite.validate_invite.get_connection")
def test_used_invite_returns_400(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    mock_db.cursor.return_value.__enter__ = lambda s: mock_db.cursor.return_value
    mock_db.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.cursor.return_value.fetchone.return_value = make_invite(status="used")

    event = generate_api_gw_event({"activation_code": "ABCD1234"})
    result = validate_invite.handler(event, generate_context())

    assert result["statusCode"] == 400
    assert "already been used" in json.loads(result["body"])["error"]


@patch("functions.validate_invite.validate_invite.get_connection")
def test_expired_status_returns_400(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    mock_db.cursor.return_value.__enter__ = lambda s: mock_db.cursor.return_value
    mock_db.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.cursor.return_value.fetchone.return_value = make_invite(status="expired")

    event = generate_api_gw_event({"activation_code": "ABCD1234"})
    result = validate_invite.handler(event, generate_context())

    assert result["statusCode"] == 400
    assert "expired" in json.loads(result["body"])["error"]


@patch("functions.validate_invite.validate_invite.get_connection")
def test_past_expiry_date_marks_expired_and_returns_400(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    mock_db.cursor.return_value.__enter__ = lambda s: mock_db.cursor.return_value
    mock_db.cursor.return_value.__exit__ = MagicMock(return_value=False)
    mock_db.cursor.return_value.fetchone.return_value = make_invite(
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
    )

    event = generate_api_gw_event({"activation_code": "ABCD1234"})
    result = validate_invite.handler(event, generate_context())

    assert result["statusCode"] == 400
    assert "expired" in json.loads(result["body"])["error"]
    mock_db.commit.assert_called_once()


@patch("functions.validate_invite.validate_invite.get_connection")
def test_missing_activation_code_returns_400(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db

    event = generate_api_gw_event({})
    result = validate_invite.handler(event, generate_context())

    assert result["statusCode"] == 400
