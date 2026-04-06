import json
from datetime import date, timedelta
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.db import get_connection
from shared.instrumentation.tracer import tracer
from shared.reference_data.membership_period_status import MembershipPeriodStatus
from shared.services.member_service import get_member_by_id, get_member_context
from shared.services.payment_service import get_member_with_membership_type, get_invoice_by_period_id
from shared.services.membership_service import (
    get_membership_period,
    insert_membership_period,
    update_membership_period,
    get_current_fee,
    generate_invoice_number,
    insert_invoice,
)

logger = Logger()

VALID_PERIOD_STATUSES = {s.value for s in MembershipPeriodStatus}


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "body": json.dumps(body, default=str)}


def _get_cognito_sub(event: dict) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def _require_executive(member: dict) -> dict | None:
    if member["member_role"] not in ("executive", "admin"):
        return _response(403, {"error": "Executive access required"})
    return None


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    route_key = event.get("routeKey", "")
    path_params = event.get("pathParameters") or {}
    conn = None

    try:
        conn = get_connection()
        cognito_sub = _get_cognito_sub(event)
        member = get_member_context(conn, cognito_sub)
        if not member:
            return _response(403, {"error": "Member not found"})

        body = {}
        if event.get("body"):
            body = json.loads(event["body"])

        if route_key == "POST /members/{id}/membership-periods":
            return _create_membership_period(conn, member, path_params["id"], body)

        if route_key == "PATCH /membership-periods/{id}":
            return _patch_membership_period(conn, member, path_params["id"], body)

        return _response(404, {"error": "Route not found"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error", extra={"error": str(e)})
        return _response(500, {"error": str(e)})

    finally:
        if conn:
            conn.close()


def _create_membership_period(conn, caller, target_member_id, body):
    err = _require_executive(caller)
    if err:
        return err

    target = get_member_with_membership_type(conn, target_member_id)
    if not target:
        return _response(404, {"error": "Member not found"})

    if not target["is_legacy"]:
        return _response(422, {"error": "Membership periods are auto-created for non-legacy members"})

    if not target["membership_id"]:
        return _response(422, {"error": "Member has no membership record"})

    start_date = body.get("period_start")
    end_date = body.get("period_end")
    if not start_date or not end_date:
        return _response(422, {"error": "period_start and period_end are required"})

    period = insert_membership_period(conn, str(target["membership_id"]), start_date, end_date)

    fee = get_current_fee(conn, target["membership_type"])
    due_date = date.today() + timedelta(days=fee["due_days"])
    invoice_number = generate_invoice_number(conn)
    insert_invoice(conn, str(period["id"]), invoice_number, fee["annual_fee"], due_date)
    invoice = get_invoice_by_period_id(conn, str(period["id"]))

    conn.commit()
    return _response(201, {
        "membership_period": dict(period),
        "invoice": dict(invoice),
    })


def _patch_membership_period(conn, caller, period_id, body):
    err = _require_executive(caller)
    if err:
        return err

    period = get_membership_period(conn, period_id)
    if not period:
        return _response(404, {"error": "Membership period not found"})

    if "status" in body and body["status"] not in VALID_PERIOD_STATUSES:
        return _response(422, {"error": f"status must be one of: {', '.join(VALID_PERIOD_STATUSES)}"})

    updated = update_membership_period(conn, period_id, body)
    conn.commit()
    return _response(200, dict(updated))
