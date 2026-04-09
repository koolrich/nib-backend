import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayV2Envelope
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from shared.instrumentation.tracer import tracer
from shared.models.invite_request import InviteRequest
from shared.services.invite_service import send_invite
from shared.uow.invite_uow import InviteUoW

logger = Logger()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    try:
        invite_request = parse(event=event, model=InviteRequest, envelope=ApiGatewayV2Envelope)
        cognito_sub = event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]
    except ValidationError as ve:
        logger.warning("Validation error", extra={"error": str(ve)})
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    try:
        with InviteUoW() as uow:
            return send_invite(uow, invite_request, cognito_sub)
    except Exception as e:
        logger.exception("Unexpected error occurred", extra={"error": str(e)})
        return {"statusCode": 500, "body": json.dumps({"error": "An unexpected error occurred"})}
