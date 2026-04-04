import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.db import get_connection
from shared.instrumentation.tracer import tracer
from shared.services.member_service import get_member_context
from shared.services.pledge_service import get_member_pledges

logger = Logger()


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "body": json.dumps(body, default=str)}


def _get_cognito_sub(event: dict) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    route_key = event.get("routeKey", "")
    conn = None

    try:
        conn = get_connection()
        cognito_sub = _get_cognito_sub(event)
        member = get_member_context(conn, cognito_sub)
        if not member:
            return _response(403, {"error": "Member not found"})

        # GET /members/me/pledges
        if route_key == "GET /members/me/pledges":
            return _get_my_pledges(conn, str(member["id"]))

        return _response(404, {"error": "Route not found"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error", extra={"error": str(e)})
        return _response(500, {"error": str(e)})

    finally:
        if conn:
            conn.close()


def _get_my_pledges(conn, member_id: str):
    rows = get_member_pledges(conn, member_id)
    pledges = []
    for row in rows:
        r = dict(row)
        contribution = None
        if r.get("contribution_amount") is not None:
            contribution = {
                "amount": r["contribution_amount"],
                "received_at": r["contribution_received_at"],
            }
        r.pop("contribution_amount", None)
        r.pop("contribution_received_at", None)
        r["contribution"] = contribution
        pledges.append(r)
    return _response(200, {"pledges": pledges})
