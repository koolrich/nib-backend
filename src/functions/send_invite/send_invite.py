import json
import uuid
import boto3

from shared.db import get_connection
from pydantic import ValidationError
from typing import Dict, Any
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayEnvelope
from aws_lambda_powertools import Logger, Tracer
from shared.models.invite_request import InviteRequest
from shared.instrumentation.tracer import tracer

logger = Logger()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    return send_invite(event)


@tracer.capture_method
def send_invite(event: Dict[str, Any]):
    conn = get_connection()
    try:
        invite_request = parse(
            event=event, model=InviteRequest, envelope=ApiGatewayEnvelope
        )

        tracer.put_annotation("mobile", invite_request.mobile)
        tracer.put_annotation("relationship", invite_request.relationship)
        tracer.put_metadata("invite_payload", invite_request.dict())

        activation_code = generate_activation_code()
        logger.debug(
            "Activation code generated", extra={"activation_code": activation_code}
        )

        insert_invite(conn, invite_request, activation_code)
        publish_invite_sms(invite_request.mobile, activation_code)

        conn.commit()
        return {"statusCode": 200, "body": json.dumps({"message": "Invite sent."})}

    except ValidationError as ve:
        logger.warning("Validation error", extra={"error": str(ve)})
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    except Exception as e:
        conn.rollback()
        logger.exception("Unexpected error occurred", extra={"error": str(e)})
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    finally:
        conn.close()


@tracer.capture_method(name="InsertInvite")
def insert_invite(conn, invite_request: InviteRequest, activation_code: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO invites (first_name, last_name, mobile, activation_code, invited_by, relationship, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                invite_request.first_name,
                invite_request.last_name,
                invite_request.mobile,
                activation_code,
                "093c5291-5f10-4dff-8424-affdfbe7776a",
                invite_request.relationship,
                "other",
            ),
        )


@tracer.capture_method(name="SendInviteSMS")
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
        logger.error(
            "SMS may not have been sent successfully",
            extra={"sns_response": response},
        )


def generate_activation_code() -> str:
    return uuid.uuid4().hex[:8].upper()
