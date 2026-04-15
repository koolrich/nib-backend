import json
from unittest.mock import patch, MagicMock

import bcrypt
from botocore.exceptions import ClientError

import functions.login.login as login_handler
from utils import generate_context, generate_api_gw_event

MEMBER = {"id": "member-uuid", "cognito_user_id": "cognito-username"}

VALID_CODE = "123456"
VALID_HASH = bcrypt.hashpw(VALID_CODE.encode(), bcrypt.gensalt()).decode()
VALID_TOKEN = {"id": "token-uuid", "code_hash": VALID_HASH}


def _make_uow(member=MEMBER, token=VALID_TOKEN):
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.members.get_by_mobile.return_value = member
    uow.password_reset.get_valid.return_value = token
    return uow


def _event(route_key, body):
    ev = generate_api_gw_event(body, route_key=route_key)
    ev["headers"]["authorization"] = "Bearer test-access-token"
    return ev


# ── POST /auth/forgot-password ────────────────────────────────────────────────

@patch("functions.login.login.PasswordResetUoW")
@patch("functions.login.login.forgot_password")
def test_forgot_password_returns_200(mock_service, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    mock_service.return_value = {"statusCode": 200, "body": json.dumps({"message": "Reset code sent"})}
    result = login_handler.handler(_event("POST /v1/auth/forgot-password", {"mobile": "+447123456789"}), generate_context())
    assert result["statusCode"] == 200


@patch("functions.login.login.PasswordResetUoW")
@patch("functions.login.login.forgot_password")
def test_forgot_password_unknown_mobile_returns_404(mock_service, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(member=None)
    mock_service.return_value = {"statusCode": 404, "body": json.dumps({"error": "No account found for this mobile number"})}
    result = login_handler.handler(_event("POST /v1/auth/forgot-password", {"mobile": "+447000000000"}), generate_context())
    assert result["statusCode"] == 404


# ── POST /auth/reset-password ─────────────────────────────────────────────────

@patch("functions.login.login.PasswordResetUoW")
@patch("functions.login.login.reset_password")
def test_reset_password_returns_200(mock_service, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    mock_service.return_value = {"statusCode": 200, "body": json.dumps({"message": "Password updated"})}
    result = login_handler.handler(_event("POST /v1/auth/reset-password", {
        "mobile": "+447123456789", "code": VALID_CODE, "new_password": "NewPass1!"
    }), generate_context())
    assert result["statusCode"] == 200


@patch("functions.login.login.PasswordResetUoW")
@patch("functions.login.login.reset_password")
def test_reset_password_invalid_code_returns_400(mock_service, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    mock_service.return_value = {"statusCode": 400, "body": json.dumps({"error": "Reset code is invalid or has expired"})}
    result = login_handler.handler(_event("POST /v1/auth/reset-password", {
        "mobile": "+447123456789", "code": "000000", "new_password": "NewPass1!"
    }), generate_context())
    assert result["statusCode"] == 400


# ── POST /auth/change-password ────────────────────────────────────────────────

@patch("functions.login.login.PasswordResetUoW")
@patch("functions.login.login.change_password_service")
def test_change_password_returns_200(mock_service, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    mock_service.return_value = {"statusCode": 200, "body": json.dumps({"message": "Password updated"})}
    result = login_handler.handler(_event("POST /v1/auth/change-password", {
        "current_password": "OldPass1!", "new_password": "NewPass1!"
    }), generate_context())
    assert result["statusCode"] == 200


@patch("functions.login.login.PasswordResetUoW")
@patch("functions.login.login.change_password_service")
def test_change_password_wrong_current_returns_401(mock_service, mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    mock_service.return_value = {"statusCode": 401, "body": json.dumps({"error": "Current password is incorrect"})}
    result = login_handler.handler(_event("POST /v1/auth/change-password", {
        "current_password": "WrongPass1!", "new_password": "NewPass1!"
    }), generate_context())
    assert result["statusCode"] == 401
