import json
import uuid
import boto3

from shared.db import get_connection
from pydantic import ValidationError
from typing import Dict, Any
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayV2Envelope
from aws_lambda_powertools import Logger
from shared.models.invite_request import InviteRequest
from shared.instrumentation.tracer import tracer
from shared.services.invite_service import (
    insert_invite,
    publish_invite_sms,
    generate_activation_code,
)
from shared.services.member_service import get_member_by_cognito_sub


logger = Logger()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    return send_invite(event)


@tracer.capture_method
def send_invite(event: Dict[str, Any]):
    conn = None
    try:
        conn = get_connection()
        invite_request = parse(
            event=event, model=InviteRequest, envelope=ApiGatewayV2Envelope
        )

        cognito_sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
        member = get_member_by_cognito_sub(conn, cognito_sub)
        if not member:
            return {"statusCode": 403, "body": json.dumps({"error": "Member not found"})}

        activation_code = generate_activation_code()
        logger.debug(
            "Activation code generated", extra={"activation_code": activation_code}
        )

        insert_invite(conn, invite_request, activation_code, str(member["id"]))
        publish_invite_sms(invite_request.mobile, activation_code)

        conn.commit()
        return {"statusCode": 200, "body": json.dumps({"message": "Invite sent."})}

    except ValidationError as ve:
        logger.warning("Validation error", extra={"error": str(ve)})
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error occurred", extra={"error": str(e)})
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    finally:
        if conn:
            conn.close()
