import json
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from shared.services.cognito_service import initiate_auth, refresh_auth, set_password

logger = Logger()

_sns = None


def _get_sns():
    global _sns
    if _sns is None:
        _sns = boto3.client("sns")
    return _sns


def _publish_reset_sms(mobile: str, code: str):
    topic_arn = os.environ["SMS_TOPIC_ARN"]
    message = f"Your NIB password reset code is: {code}. It expires in 15 minutes."
    response = _get_sns().publish(
        TopicArn=topic_arn,
        Message=json.dumps({"mobile": mobile, "message": message}),
    )
    status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    if status_code != 200:
        logger.error("SNS publish failed", extra={"sns_response": response})
        raise RuntimeError(f"SNS publish failed with status {status_code}")


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


def forgot_password(uow, mobile: str) -> dict:
    if not mobile:
        return {"statusCode": 400, "body": json.dumps({"error": "mobile is required"})}

    member = uow.members.get_by_mobile(mobile)
    if not member:
        return {"statusCode": 404, "body": json.dumps({"error": "No account found for this mobile number"})}

    code = str(secrets.randbelow(1_000_000)).zfill(6)
    code_hash = bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)

    uow.password_reset.insert(str(member["id"]), code_hash, expires_at)
    _publish_reset_sms(mobile, code)

    return {"statusCode": 200, "body": json.dumps({"message": "Reset code sent"})}


def reset_password(uow, mobile: str, code: str, new_password: str) -> dict:
    if not mobile or not code or not new_password:
        return {"statusCode": 400, "body": json.dumps({"error": "mobile, code and new_password are required"})}

    member = uow.members.get_by_mobile(mobile)
    if not member:
        return {"statusCode": 404, "body": json.dumps({"error": "No account found for this mobile number"})}

    token = uow.password_reset.get_valid(str(member["id"]))
    if not token:
        return {"statusCode": 400, "body": json.dumps({"error": "Reset code is invalid or has expired"})}

    if not bcrypt.checkpw(code.encode(), token["code_hash"].encode()):
        return {"statusCode": 400, "body": json.dumps({"error": "Reset code is invalid or has expired"})}

    try:
        set_password(member["cognito_user_id"], new_password)
    except ClientError as ce:
        error_code = ce.response["Error"]["Code"]
        if error_code == "InvalidPasswordException":
            return {"statusCode": 422, "body": json.dumps({"error": "Password does not meet requirements"})}
        logger.exception("Cognito error during password reset", extra={"error": str(ce)})
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to update password"})}

    uow.password_reset.mark_used(str(token["id"]))
    return {"statusCode": 200, "body": json.dumps({"message": "Password updated"})}


def change_password_service(uow, cognito_sub: str, current_password: str, new_password: str) -> dict:
    if not current_password or not new_password:
        return {"statusCode": 400, "body": json.dumps({"error": "current_password and new_password are required"})}

    member = uow.members.get_by_cognito_sub(cognito_sub)
    if not member:
        return {"statusCode": 403, "body": json.dumps({"error": "Member not found"})}

    mobile_row = uow.members.get_mobile_and_cognito_by_id(str(member["id"]))
    if not mobile_row:
        return {"statusCode": 403, "body": json.dumps({"error": "Member not found"})}

    # Verify current password by attempting auth
    try:
        initiate_auth(mobile_row["mobile"], current_password)
    except ClientError as ce:
        if ce.response["Error"]["Code"] in ("NotAuthorizedException", "UserNotFoundException"):
            return {"statusCode": 401, "body": json.dumps({"error": "Current password is incorrect"})}
        logger.exception("Cognito error verifying current password", extra={"error": str(ce)})
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to verify current password"})}

    # Set new password via admin operation
    try:
        set_password(mobile_row["cognito_user_id"], new_password)
        return {"statusCode": 200, "body": json.dumps({"message": "Password updated"})}
    except ClientError as ce:
        if ce.response["Error"]["Code"] == "InvalidPasswordException":
            return {"statusCode": 422, "body": json.dumps({"error": "Password does not meet requirements"})}
        logger.exception("Cognito error setting new password", extra={"error": str(ce)})
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to update password"})}


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
