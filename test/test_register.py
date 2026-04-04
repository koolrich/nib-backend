from unittest.mock import patch, MagicMock
import json
import pytest
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

VALID_INVITE = {
    "id": "invite-uuid-1234",
    "relationship": "other",
    "invited_by": "admin-uuid-5678",
    "is_legacy": False,
}

SPOUSE_INVITE = {
    "id": "invite-uuid-1234",
    "relationship": "spouse",
    "invited_by": "admin-uuid-5678",
    "is_legacy": False,
}


def _setup_mock_db(mock_db, invite, member_id="member-uuid-1234", membership_id="membership-uuid-1234", period_id="period-uuid-1234"):
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)

    cursor.fetchone.side_effect = [
        invite,                          # get_invite_by_activation_code
        {"id": member_id},               # insert_member RETURNING id
        {"annual_fee": 60.00},           # get_current_fee
        {"id": membership_id},           # insert_membership RETURNING id
        {"id": period_id},               # insert_membership_period RETURNING id
        {"invoice_number": "NIB-0001"},  # generate_invoice_number
    ]
    mock_db.cursor.return_value = cursor
    return cursor


@patch("functions.register.register.get_connection")
@patch("functions.register.register.sign_up", return_value=("cognito-username-123", "cognito-sub-123"))
@patch("functions.register.register.confirm_sign_up")
def test_register_other_returns_201(mock_confirm, mock_signup, mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    _setup_mock_db(mock_db, VALID_INVITE)

    result = register.handler(generate_api_gw_event(VALID_BODY), generate_context())

    assert result["statusCode"] == 201
    mock_signup.assert_called_once_with("+447123456789", "SecurePass1")
    mock_confirm.assert_called_once_with("cognito-username-123")
    mock_db.commit.assert_called_once()


@patch("functions.register.register.get_connection")
@patch("functions.register.register.sign_up", return_value=("cognito-username-123", "cognito-sub-123"))
@patch("functions.register.register.confirm_sign_up")
def test_register_spouse_returns_201(mock_confirm, mock_signup, mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.side_effect = [
        SPOUSE_INVITE,                    # get_invite_by_activation_code
        {"id": "member-uuid-1234"},       # insert_member RETURNING id
        {"membership_id": "membership-uuid-5678"},  # get_member_membership_id
    ]
    mock_db.cursor.return_value = cursor

    body = {**VALID_BODY}
    body.pop("membership_type")
    result = register.handler(generate_api_gw_event(body), generate_context())

    assert result["statusCode"] == 201
    mock_db.commit.assert_called_once()


@patch("functions.register.register.get_connection")
def test_register_invalid_activation_code_returns_404(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = None
    mock_db.cursor.return_value = cursor

    result = register.handler(generate_api_gw_event(VALID_BODY), generate_context())

    assert result["statusCode"] == 404


@patch("functions.register.register.get_connection")
def test_register_other_without_membership_type_returns_400(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.return_value = VALID_INVITE
    mock_db.cursor.return_value = cursor

    body = {**VALID_BODY}
    body.pop("membership_type")
    result = register.handler(generate_api_gw_event(body), generate_context())

    assert result["statusCode"] == 400
    assert "membership_type" in json.loads(result["body"])["error"]


@patch("functions.register.register.get_connection")
def test_register_missing_required_fields_returns_400(mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db

    result = register.handler(generate_api_gw_event({"activation_code": "ABCD1234"}), generate_context())

    assert result["statusCode"] == 400


@patch("functions.register.register.get_connection")
@patch("functions.register.register.sign_up", return_value=("cognito-username-123", "cognito-sub-123"))
@patch("functions.register.register.confirm_sign_up")
@patch("functions.register.register.delete_user")
def test_register_db_failure_rolls_back_cognito(mock_delete, mock_confirm, mock_signup, mock_get_connection, mock_db):
    mock_get_connection.return_value = mock_db
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.side_effect = [
        VALID_INVITE,
        Exception("DB insert failed"),
    ]
    mock_db.cursor.return_value = cursor

    result = register.handler(generate_api_gw_event(VALID_BODY), generate_context())

    assert result["statusCode"] == 500
    mock_delete.assert_called_once_with("cognito-username-123")
    mock_db.rollback.assert_called_once()
