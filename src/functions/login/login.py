import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayV2Envelope
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from shared.instrumentation.tracer import tracer
from shared.models.login_request import LoginRequest
from shared.services.login_service import login

logger = Logger()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    try:
        request = parse(event=event, model=LoginRequest, envelope=ApiGatewayV2Envelope)
    except ValidationError as ve:
        logger.warning("Validation error", extra={"error": str(ve)})
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    try:
        return login(request)
    except Exception as e:
        logger.exception("Unexpected error during login", extra={"error": str(e)})
        return {"statusCode": 500, "body": json.dumps({"error": "An unexpected error occurred"})}
