import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.instrumentation.tracer import tracer
from shared.services.membership_service import create_membership_period, patch_membership_period
from shared.uow.membership_uow import MembershipUoW

logger = Logger()


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "body": json.dumps(body, default=str)}


def _get_cognito_sub(event: dict) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}
    body = json.loads(event["body"]) if event.get("body") else {}
    cognito_sub = _get_cognito_sub(event)

    try:
        with MembershipUoW() as uow:
            caller = uow.members.get_by_cognito_sub(cognito_sub)
            if not caller:
                return _response(403, {"error": "Member not found"})

            if route_key == "POST /v1/members/{id}/membership-periods":
                return create_membership_period(uow, caller, path_params["id"], body)

            if route_key == "PATCH /v1/membership-periods/{id}":
                return patch_membership_period(uow, caller, path_params["id"], body)

            return _response(404, {"error": "Route not found"})

    except Exception as e:
        logger.exception("Unexpected error", extra={"error": str(e)})
        return _response(500, {"error": str(e)})
