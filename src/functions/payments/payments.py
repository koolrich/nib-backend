import json
from decimal import Decimal
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.db import get_connection
from shared.instrumentation.tracer import tracer
from shared.reference_data.invoice_status import InvoiceStatus
from shared.services.member_service import get_member_by_id, get_member_context
from shared.services.payment_service import (
    VALID_PAYMENT_METHODS,
    get_member_with_membership_type,
    get_active_period_for_membership,
    get_invoice_by_period_id,
    get_invoice_by_id,
    get_total_paid,
    get_payments_by_invoice,
    get_payment_by_id,
    insert_payment,
    delete_payment,
    update_invoice_status,
)

logger = Logger()


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

        if route_key == "POST /invoices/{id}/payments":
            return _record_payment(conn, member, path_params["id"], body)

        if route_key == "DELETE /payments/{id}":
            return _delete_payment(conn, member, path_params["id"])

        if route_key == "GET /members/{id}/statement":
            return _get_statement(conn, member, path_params["id"])

        return _response(404, {"error": "Route not found"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error", extra={"error": str(e)})
        return _response(500, {"error": str(e)})

    finally:
        if conn:
            conn.close()


def _record_payment(conn, caller, invoice_id, body):
    err = _require_executive(caller)
    if err:
        return err

    invoice = get_invoice_by_id(conn, invoice_id)
    if not invoice:
        return _response(404, {"error": "Invoice not found"})

    if invoice["status"] == InvoiceStatus.PAID.value:
        return _response(422, {"error": "Cannot record a payment against a fully paid invoice"})

    amount = body.get("amount")
    method = body.get("method")
    received_at = body.get("received_at")
    if not amount or not method or not received_at:
        return _response(422, {"error": "amount, method and received_at are required"})

    if method not in VALID_PAYMENT_METHODS:
        return _response(422, {"error": f"method must be one of: {', '.join(VALID_PAYMENT_METHODS)}"})

    total_paid = get_total_paid(conn, invoice_id)
    outstanding = Decimal(str(invoice["amount_due"])) - Decimal(str(total_paid))
    if Decimal(str(amount)) > outstanding:
        return _response(422, {"error": f"Payment amount exceeds outstanding balance of {outstanding:.2f}"})

    payment = insert_payment(
        conn, invoice_id, amount, method,
        body.get("reference"), str(caller["id"]), received_at, body.get("note"),
    )

    new_total = Decimal(str(total_paid)) + Decimal(str(amount))
    new_status = (
        InvoiceStatus.PAID.value
        if new_total >= Decimal(str(invoice["amount_due"]))
        else InvoiceStatus.PARTIAL.value
    )
    update_invoice_status(conn, invoice_id, new_status)
    conn.commit()

    return _response(201, {
        **{k: v for k, v in dict(payment).items()},
        "invoice": {
            "status": new_status,
            "amount_due": float(invoice["amount_due"]),
            "total_paid": float(new_total),
            "outstanding": float(Decimal(str(invoice["amount_due"])) - new_total),
        },
    })


def _delete_payment(conn, caller, payment_id):
    err = _require_executive(caller)
    if err:
        return err

    payment = get_payment_by_id(conn, payment_id)
    if not payment:
        return _response(404, {"error": "Payment not found"})

    invoice_id = str(payment["invoice_id"])
    delete_payment(conn, payment_id)

    total_paid = get_total_paid(conn, invoice_id)
    invoice = get_invoice_by_id(conn, invoice_id)
    amount_due = Decimal(str(invoice["amount_due"]))
    total = Decimal(str(total_paid))

    if total >= amount_due:
        new_status = InvoiceStatus.PAID.value
    elif total > 0:
        new_status = InvoiceStatus.PARTIAL.value
    else:
        new_status = InvoiceStatus.UNPAID.value

    update_invoice_status(conn, invoice_id, new_status)
    conn.commit()
    return _response(200, {"message": "Payment deleted", "invoice_status": new_status})


def _get_statement(conn, caller, target_member_id):
    target = get_member_by_id(conn, target_member_id)
    if not target:
        return _response(404, {"error": "Member not found"})

    if str(caller["id"]) != str(target["id"]) and caller["member_role"] not in ("executive", "admin"):
        return _response(403, {"error": "Access denied"})

    member_info = get_member_with_membership_type(conn, target_member_id)
    membership_type = member_info["membership_type"] if member_info else None

    if not target["membership_id"]:
        return _response(200, {
            "member_id": target_member_id,
            "membership_type": membership_type,
            "period": None,
            "invoice": None,
            "payments": [],
        })

    period = get_active_period_for_membership(conn, str(target["membership_id"]))
    if not period:
        return _response(200, {
            "member_id": target_member_id,
            "membership_type": membership_type,
            "period": None,
            "invoice": None,
            "payments": [],
        })

    invoice = get_invoice_by_period_id(conn, str(period["id"]))
    if not invoice:
        return _response(200, {
            "member_id": target_member_id,
            "membership_type": membership_type,
            "period": dict(period),
            "invoice": None,
            "payments": [],
        })

    payments = get_payments_by_invoice(conn, str(invoice["id"]))
    total_paid = sum(Decimal(str(p["amount"])) for p in payments)
    outstanding = Decimal(str(invoice["amount_due"])) - total_paid

    return _response(200, {
        "member_id": target_member_id,
        "membership_type": membership_type,
        "period": dict(period),
        "invoice": {
            **{k: v for k, v in dict(invoice).items()},
            "total_paid": float(total_paid),
            "outstanding": float(outstanding),
        },
        "payments": [dict(p) for p in payments],
    })
