import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.instrumentation.tracer import tracer
from shared.services.event_service import (
    create_event, list_events, get_event, patch_event,
    add_items, create_pledge, update_pledge, cancel_pledge, record_contribution,
)
from shared.uow.event_uow import EventUoW

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
        with EventUoW() as uow:
            member = uow.members.get_by_cognito_sub(cognito_sub)
            if not member:
                return _response(403, {"error": "Member not found"})

            if route_key == "POST /v1/events":
                return create_event(uow, member, body)

            if route_key == "GET /v1/events":
                return list_events(uow)

            if route_key == "GET /v1/events/{id}":
                return get_event(uow, path_params["id"])

            if route_key == "PATCH /v1/events/{id}":
                return patch_event(uow, member, path_params["id"], body)

            if route_key == "POST /v1/events/{id}/items":
                return add_items(uow, member, path_params["id"], body)

            if route_key == "POST /v1/events/{id}/pledges":
                return create_pledge(uow, member, path_params["id"], body)

            if route_key == "PATCH /v1/events/{id}/pledges/{pledgeId}":
                return update_pledge(uow, member, path_params["id"], path_params["pledgeId"], body)

            if route_key == "DELETE /v1/events/{id}/pledges/{pledgeId}":
                return cancel_pledge(uow, member, path_params["id"], path_params["pledgeId"])

            if route_key == "POST /v1/events/{id}/contributions":
                return record_contribution(uow, member, path_params["id"], body)

            return _response(404, {"error": "Route not found"})

    except Exception as e:
        logger.exception("Unexpected error", extra={"error": str(e)})
        return _response(500, {"error": str(e)})
