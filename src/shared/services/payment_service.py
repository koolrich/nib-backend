import json
from decimal import Decimal

from aws_lambda_powertools import Logger
from shared.reference_data.invoice_status import InvoiceStatus

logger = Logger()

VALID_PAYMENT_METHODS = {"bank_transfer", "cash", "cheque", "other"}


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "body": json.dumps(body, default=str)}


def _require_executive(member: dict) -> dict | None:
    if member["member_role"] not in ("executive", "admin"):
        return _response(403, {"error": "Executive access required"})
    return None


def record_payment(uow, caller: dict, invoice_id: str, body: dict) -> dict:
    err = _require_executive(caller)
    if err:
        return err

    invoice = uow.invoices.get_by_id(invoice_id)
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

    total_paid = uow.payments.get_total_by_invoice(invoice_id)
    outstanding = Decimal(str(invoice["amount_due"])) - Decimal(str(total_paid))
    if Decimal(str(amount)) > outstanding:
        return _response(422, {"error": f"Payment amount exceeds outstanding balance of {outstanding:.2f}"})

    payment = uow.payments.insert(
        invoice_id, amount, method,
        body.get("reference"), str(caller["id"]), received_at, body.get("note"),
    )

    new_total = Decimal(str(total_paid)) + Decimal(str(amount))
    new_status = (
        InvoiceStatus.PAID.value
        if new_total >= Decimal(str(invoice["amount_due"]))
        else InvoiceStatus.PARTIAL.value
    )
    uow.invoices.update_status(invoice_id, new_status)

    return _response(201, {
        **dict(payment),
        "invoice": {
            "status": new_status,
            "amount_due": float(invoice["amount_due"]),
            "total_paid": float(new_total),
            "outstanding": float(Decimal(str(invoice["amount_due"])) - new_total),
        },
    })


def delete_payment(uow, caller: dict, payment_id: str) -> dict:
    err = _require_executive(caller)
    if err:
        return err

    payment = uow.payments.get_by_id(payment_id)
    if not payment:
        return _response(404, {"error": "Payment not found"})

    invoice_id = str(payment["invoice_id"])
    uow.payments.delete(payment_id)

    total_paid = uow.payments.get_total_by_invoice(invoice_id)
    invoice = uow.invoices.get_by_id(invoice_id)
    amount_due = Decimal(str(invoice["amount_due"]))
    total = Decimal(str(total_paid))

    if total >= amount_due:
        new_status = InvoiceStatus.PAID.value
    elif total > 0:
        new_status = InvoiceStatus.PARTIAL.value
    else:
        new_status = InvoiceStatus.UNPAID.value

    uow.invoices.update_status(invoice_id, new_status)
    return _response(200, {"message": "Payment deleted", "invoice_status": new_status})


def get_statement(uow, caller: dict, target_member_id: str) -> dict:
    target = uow.members.get_by_id(target_member_id)
    if not target:
        return _response(404, {"error": "Member not found"})

    if str(caller["id"]) != str(target["id"]) and caller["member_role"] not in ("executive", "admin"):
        return _response(403, {"error": "Access denied"})

    member_info = uow.members.get_with_membership_type(target_member_id)
    membership_type = member_info["membership_type"] if member_info else None

    if not target["membership_id"]:
        return _response(200, {"member_id": target_member_id, "membership_type": membership_type,
                               "period": None, "invoice": None, "payments": []})

    period = uow.periods.get_active_for_membership(str(target["membership_id"]))
    if not period:
        return _response(200, {"member_id": target_member_id, "membership_type": membership_type,
                               "period": None, "invoice": None, "payments": []})

    invoice = uow.invoices.get_by_period_id(str(period["id"]))
    if not invoice:
        return _response(200, {"member_id": target_member_id, "membership_type": membership_type,
                               "period": dict(period), "invoice": None, "payments": []})

    payments = uow.payments.get_all_by_invoice(str(invoice["id"]))
    total_paid = sum(Decimal(str(p["amount"])) for p in payments)
    outstanding = Decimal(str(invoice["amount_due"])) - total_paid

    return _response(200, {
        "member_id": target_member_id,
        "membership_type": membership_type,
        "period": dict(period),
        "invoice": {
            **dict(invoice),
            "total_paid": float(total_paid),
            "outstanding": float(outstanding),
        },
        "payments": [dict(p) for p in payments],
    })
