import json
import uuid
from datetime import datetime, timezone

from aws_lambda_powertools import Logger
from shared.reference_data.invite_status import InviteStatus

import boto3

logger = Logger()


def generate_activation_code() -> str:
    return uuid.uuid4().hex[:8].upper()


def publish_invite_sms(mobile: str, activation_code: str):
    sns = boto3.client("sns")
    response = sns.publish(
        PhoneNumber=mobile,
        Message=f"Your activation code is: {activation_code}",
        MessageAttributes={
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": "Transactional",
            }
        },
    )
    status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    if status_code != 200:
        logger.error("SMS may not have been sent successfully", extra={"sns_response": response})
        raise RuntimeError(f"SNS publish failed with status {status_code}")


def send_invite(uow, invite_request, cognito_sub: str) -> dict:
    member = uow.members.get_by_cognito_sub(cognito_sub)
    if not member:
        return {"statusCode": 403, "body": json.dumps({"error": "Member not found"})}

    if invite_request.is_legacy and member["member_role"] not in ("executive", "admin"):
        return {"statusCode": 403, "body": json.dumps({"error": "Only executives and admins can send legacy invites"})}

    if invite_request.is_legacy and not invite_request.date_joined:
        return {"statusCode": 400, "body": json.dumps({"error": "date_joined is required for legacy invites"})}

    if uow.members.mobile_exists(invite_request.mobile):
        return {"statusCode": 409, "body": json.dumps({"error": "This mobile number is already registered as a member"})}

    if uow.invites.pending_exists(invite_request.mobile):
        return {"statusCode": 409, "body": json.dumps({"error": "A pending invite already exists for this mobile number"})}

    activation_code = generate_activation_code()
    uow.invites.insert(invite_request, activation_code, str(member["id"]))
    publish_invite_sms(invite_request.mobile, activation_code)

    return {"statusCode": 200, "body": json.dumps({"message": "Invite sent."})}


def validate_invite(uow, activation_code: str) -> dict:
    invite = uow.invites.get_by_activation_code(activation_code)

    if not invite:
        return {"statusCode": 404, "body": json.dumps({"error": "Invalid activation code"})}

    if invite["status"] == InviteStatus.USED.value:
        return {"statusCode": 400, "body": json.dumps({"error": "Invite has already been used"})}

    if invite["status"] == InviteStatus.EXPIRED.value:
        return {"statusCode": 400, "body": json.dumps({"error": "Invite has expired"})}

    if invite["expires_at"] and invite["expires_at"] < datetime.now(timezone.utc).replace(tzinfo=None):
        uow.invites.mark_expired(str(invite["id"]))
        return {"statusCode": 400, "body": json.dumps({"error": "Invite has expired"})}

    return {
        "statusCode": 200,
        "body": json.dumps({
            "relationship": invite["relationship"],
            "mobile": invite["mobile"],
            "first_name": invite["first_name"],
            "last_name": invite["last_name"],
        }),
    }
