import json

from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from shared.services.cognito_service import initiate_auth, refresh_auth

logger = Logger()


def login(request) -> dict:
    try:
        auth_result = initiate_auth(request.mobile, request.password)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "access_token": auth_result["AccessToken"],
                "id_token": auth_result["IdToken"],
                "refresh_token": auth_result["RefreshToken"],
                "expires_in": auth_result["ExpiresIn"],
            }),
        }
    except ClientError as ce:
        error_code = ce.response["Error"]["Code"]
        if error_code in ("NotAuthorizedException", "UserNotFoundException"):
            return {"statusCode": 401, "body": json.dumps({"error": "Invalid phone number or password"})}
        logger.exception("Cognito error during login", extra={"error": str(ce)})
        return {"statusCode": 500, "body": json.dumps({"error": "Authentication failed"})}


def refresh(refresh_token: str) -> dict:
    try:
        auth_result = refresh_auth(refresh_token)
        return {
            "statusCode": 200,
            "body": json.dumps({
                "access_token": auth_result["AccessToken"],
                "id_token": auth_result["IdToken"],
                "expires_in": auth_result["ExpiresIn"],
            }),
        }
    except ClientError as ce:
        error_code = ce.response["Error"]["Code"]
        if error_code == "NotAuthorizedException":
            return {"statusCode": 401, "body": json.dumps({"error": "Refresh token is invalid or expired"})}
        logger.exception("Cognito error during token refresh", extra={"error": str(ce)})
        return {"statusCode": 500, "body": json.dumps({"error": "Token refresh failed"})}
