import json
from datetime import datetime, timezone
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayEnvelope
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from shared.db import get_connection
from shared.instrumentation.tracer import tracer
from shared.models.validate_invite_request import ValidateInviteRequest
from shared.reference_data.invite_status import InviteStatus
from shared.services.invite_service import get_invite_by_activation_code, mark_invite_expired

logger = Logger()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    return validate_invite(event)


@tracer.capture_method
def validate_invite(event: Dict[str, Any]):
    conn = None
    try:
        conn = get_connection()

        request = parse(
            event=event, model=ValidateInviteRequest, envelope=ApiGatewayEnvelope
        )

        invite = get_invite_by_activation_code(conn, request.activation_code)

        if not invite:
            return {"statusCode": 404, "body": json.dumps({"error": "Invalid activation code"})}

        if invite["status"] == InviteStatus.USED.value:
            return {"statusCode": 400, "body": json.dumps({"error": "Invite has already been used"})}

        if invite["status"] == InviteStatus.EXPIRED.value:
            return {"statusCode": 400, "body": json.dumps({"error": "Invite has expired"})}

        if invite["expires_at"] and invite["expires_at"] < datetime.now(timezone.utc).replace(tzinfo=None):
            mark_invite_expired(conn, invite["id"])
            conn.commit()
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
