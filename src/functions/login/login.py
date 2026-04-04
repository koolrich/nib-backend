import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayV2Envelope
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError
from pydantic import ValidationError

from shared.instrumentation.tracer import tracer
from shared.models.login_request import LoginRequest
from shared.services.cognito_service import initiate_auth

logger = Logger()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    return login(event)


@tracer.capture_method
def login(event: Dict[str, Any]):
    try:
        request = parse(event=event, model=LoginRequest, envelope=ApiGatewayV2Envelope)

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

    except ValidationError as ve:
        logger.warning("Validation error", extra={"error": str(ve)})
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    except ClientError as ce:
        error_code = ce.response["Error"]["Code"]
        if error_code in ("NotAuthorizedException", "UserNotFoundException"):
            return {"statusCode": 401, "body": json.dumps({"error": "Invalid phone number or password"})}
        logger.exception("Cognito error during login", extra={"error": str(ce)})
        return {"statusCode": 500, "body": json.dumps({"error": "Authentication failed"})}

    except Exception as e:
        logger.exception("Unexpected error during login", extra={"error": str(e)})
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
