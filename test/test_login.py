from unittest.mock import patch
from botocore.exceptions import ClientError
import json
import functions.login.login as login
from utils import generate_context, generate_api_gw_event

VALID_BODY = {
    "mobile": "+447123456789",
    "password": "SecurePass1",
}

AUTH_RESULT = {
    "AccessToken": "access-token-123",
    "IdToken": "id-token-123",
    "RefreshToken": "refresh-token-123",
    "ExpiresIn": 3600,
}


@patch("shared.services.login_service.initiate_auth", return_value=AUTH_RESULT)
def test_login_returns_200_with_tokens(mock_auth):
    result = login.handler(generate_api_gw_event(VALID_BODY), generate_context())

    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["access_token"] == "access-token-123"
    assert body["id_token"] == "id-token-123"
    assert body["refresh_token"] == "refresh-token-123"
    assert body["expires_in"] == 3600
    mock_auth.assert_called_once_with("+447123456789", "SecurePass1")


@patch("shared.services.login_service.initiate_auth", side_effect=ClientError(
    {"Error": {"Code": "NotAuthorizedException", "Message": "Incorrect username or password"}}, "AdminInitiateAuth"
))
def test_login_wrong_password_returns_401(mock_auth):
    result = login.handler(generate_api_gw_event(VALID_BODY), generate_context())

    assert result["statusCode"] == 401
    assert "Invalid phone number or password" in json.loads(result["body"])["error"]


@patch("shared.services.login_service.initiate_auth", side_effect=ClientError(
    {"Error": {"Code": "UserNotFoundException", "Message": "User does not exist"}}, "AdminInitiateAuth"
))
def test_login_unknown_user_returns_401(mock_auth):
    result = login.handler(generate_api_gw_event(VALID_BODY), generate_context())

    assert result["statusCode"] == 401


def test_login_missing_fields_returns_400():
    result = login.handler(generate_api_gw_event({"mobile": "+447123456789"}), generate_context())

    assert result["statusCode"] == 400


def test_login_invalid_mobile_returns_400():
    result = login.handler(generate_api_gw_event({"mobile": "notaphone", "password": "pass"}), generate_context())

    assert result["statusCode"] == 400
