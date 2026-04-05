import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.db import get_connection
from shared.instrumentation.tracer import tracer
from shared.services.member_service import get_member_context, get_member_by_id, update_member
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

        path_params = event.get("pathParameters") or {}
        body = json.loads(event["body"]) if event.get("body") else {}

        # GET /members/me/pledges
        if route_key == "GET /members/me/pledges":
            return _get_my_pledges(conn, str(member["id"]))

        # PATCH /members/{id}
        if route_key == "PATCH /members/{id}":
            return _patch_member(conn, member, path_params["id"], body)

        return _response(404, {"error": "Route not found"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error", extra={"error": str(e)})
        return _response(500, {"error": str(e)})

    finally:
        if conn:
            conn.close()


def _patch_member(conn, caller: dict, target_member_id: str, body: dict):
    caller_id = str(caller["id"])
    caller_role = caller["member_role"]
    is_privileged = caller_role in ("executive", "admin")

    if caller_id != target_member_id and not is_privileged:
        return _response(403, {"error": "You can only update your own profile"})

    target = get_member_by_id(conn, target_member_id)
    if not target:
        return _response(404, {"error": "Member not found"})

    restricted = {"member_role", "status"}
    if any(k in body for k in restricted) and not is_privileged:
        return _response(403, {"error": "Only executives and admins can update role or status"})

    row = update_member(conn, target_member_id, body)
    conn.commit()
    return _response(200, dict(row))


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
