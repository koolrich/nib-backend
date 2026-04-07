import json

from aws_lambda_powertools import Logger
from shared.reference_data.membership_period_status import MembershipPeriodStatus
from shared.serializers.membership_serializers import serialize_period, serialize_invoice

logger = Logger()

VALID_PERIOD_STATUSES = {s.value for s in MembershipPeriodStatus}


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "body": json.dumps(body, default=str)}


def _require_executive(member: dict) -> dict | None:
    if member["member_role"] not in ("executive", "admin"):
        return _response(403, {"error": "Executive access required"})
    return None


def create_membership_period(uow, caller: dict, target_member_id: str, body: dict) -> dict:
    err = _require_executive(caller)
    if err:
        return err

    target = uow.members.get_with_membership_type(target_member_id)
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

    period = uow.periods.insert(str(target["membership_id"]), start_date, end_date)
    invoice = uow.invoices.insert(str(period["id"]), target["membership_type"])

    return _response(201, {
        "membership_period": serialize_period(period),
        "invoice": serialize_invoice(invoice),
    })


def patch_membership_period(uow, caller: dict, period_id: str, body: dict) -> dict:
    err = _require_executive(caller)
    if err:
        return err

    period = uow.periods.get_by_id(period_id)
    if not period:
        return _response(404, {"error": "Membership period not found"})

    if "status" in body and body["status"] not in VALID_PERIOD_STATUSES:
        return _response(422, {"error": f"status must be one of: {', '.join(VALID_PERIOD_STATUSES)}"})

    updated = uow.periods.update(period_id, body)
    return _response(200, serialize_period(updated))
