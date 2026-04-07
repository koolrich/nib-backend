import json

from aws_lambda_powertools import Logger
from shared.serializers.event_serializers import (
    serialize_event, serialize_event_create, serialize_event_update,
    serialize_item, serialize_item_insert,
    serialize_pledge, serialize_pledge_write, serialize_pledge_update, serialize_pledge_cancel,
    serialize_contribution, serialize_contribution_insert,
)

logger = Logger()

VALID_EVENT_TYPES = {"pledge", "contribution"}
VALID_EVENT_STATUSES = {"upcoming", "completed"}


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "body": json.dumps(body, default=str)}


def _require_executive(member: dict) -> dict | None:
    if member["member_role"] not in ("executive", "admin"):
        return _response(403, {"error": "Executive access required"})
    return None


def create_event(uow, member: dict, body: dict) -> dict:
    err = _require_executive(member)
    if err:
        return err

    title = body.get("title")
    date = body.get("date")
    type_ = body.get("type")
    description = body.get("description")

    if not title or not date or not type_:
        return _response(422, {"error": "title, date and type are required"})
    if type_ not in VALID_EVENT_TYPES:
        return _response(422, {"error": f"type must be one of: {', '.join(VALID_EVENT_TYPES)}"})

    row = uow.events.insert(title, date, type_, description, str(member["id"]))
    return _response(201, serialize_event_create(row))


def list_events(uow) -> dict:
    rows = uow.events.get_all()
    return _response(200, {"events": [serialize_event(r) for r in rows]})


def get_event(uow, event_id: str) -> dict:
    event = uow.events.get_by_id(event_id)
    if not event:
        return _response(404, {"error": "Event not found"})

    result = serialize_event(event)
    if event["type"] == "pledge":
        result["items"] = [serialize_item(i) for i in uow.events.get_items(event_id)]
    result["pledges"] = [serialize_pledge(p) for p in uow.events.get_pledges(event_id)]
    result["contributions"] = [serialize_contribution(c) for c in uow.events.get_contributions(event_id)]
    return _response(200, result)


def patch_event(uow, member: dict, event_id: str, body: dict) -> dict:
    err = _require_executive(member)
    if err:
        return err

    event = uow.events.get_by_id(event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot edit a completed event"})

    if "type" in body and body["type"] != event["type"]:
        if uow.events.has_items_or_pledges(event_id):
            return _response(422, {"error": "Cannot change event type after items or pledges have been added"})

    if "status" in body and body["status"] not in VALID_EVENT_STATUSES:
        return _response(422, {"error": f"status must be one of: {', '.join(VALID_EVENT_STATUSES)}"})

    if "type" in body and body["type"] not in VALID_EVENT_TYPES:
        return _response(422, {"error": f"type must be one of: {', '.join(VALID_EVENT_TYPES)}"})

    row = uow.events.update(event_id, body)
    return _response(200, serialize_event_update(row))


def add_items(uow, member: dict, event_id: str, body: dict) -> dict:
    err = _require_executive(member)
    if err:
        return err

    event = uow.events.get_by_id(event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["type"] != "pledge":
        return _response(422, {"error": "Items can only be added to pledge events"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot add items to a completed event"})

    items = body.get("items", [])
    if not items:
        return _response(422, {"error": "items array is required and must not be empty"})
    for item in items:
        if not item.get("name") or not item.get("quantity_needed") or not item.get("unit"):
            return _response(422, {"error": "Each item must have name, quantity_needed and unit"})

    rows = uow.events.insert_items(event_id, items)
    return _response(201, {"items": [serialize_item_insert(r) for r in rows]})


def create_pledge(uow, member: dict, event_id: str, body: dict) -> dict:
    event = uow.events.get_by_id(event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["type"] != "pledge":
        return _response(422, {"error": "This event does not accept pledges"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot pledge on a completed event"})

    event_item_id = body.get("event_item_id")
    quantity = body.get("quantity")
    if not event_item_id or not quantity:
        return _response(422, {"error": "event_item_id and quantity are required"})

    item = uow.pledges.get_item_by_id(event_item_id, event_id)
    if not item:
        return _response(404, {"error": "Event item not found"})

    member_id = str(member["id"])
    if uow.pledges.get_existing(member_id, event_item_id):
        return _response(409, {"error": "You have an existing pledge for this item, please edit it instead"})

    remaining = uow.pledges.get_quantity_remaining(event_item_id)
    if remaining <= 0:
        return _response(422, {"error": "This item has been fully pledged"})
    if quantity > remaining:
        return _response(422, {"error": f"Only {remaining} units remaining"})

    row = uow.pledges.insert(event_id, member_id, event_item_id, quantity)
    return _response(201, serialize_pledge_write(row))


def update_pledge(uow, member: dict, event_id: str, pledge_id: str, body: dict) -> dict:
    event = uow.events.get_by_id(event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot edit a pledge on a completed event"})

    pledge = uow.pledges.get_by_id(pledge_id, event_id)
    if not pledge:
        return _response(404, {"error": "Pledge not found"})
    if str(pledge["member_id"]) != str(member["id"]):
        return _response(403, {"error": "This pledge does not belong to you"})
    if pledge["status"] == "cancelled":
        return _response(422, {"error": "Cannot edit a cancelled pledge"})

    quantity = body.get("quantity")
    if not quantity:
        return _response(422, {"error": "quantity is required"})

    remaining = uow.pledges.get_quantity_remaining(str(pledge["event_item_id"]), str(member["id"]))
    if quantity > remaining:
        return _response(422, {"error": f"Only {remaining} units remaining"})

    row = uow.pledges.update_quantity(pledge_id, quantity)
    return _response(200, serialize_pledge_update(row))


def cancel_pledge(uow, member: dict, event_id: str, pledge_id: str) -> dict:
    event = uow.events.get_by_id(event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot cancel a pledge on a completed event"})

    pledge = uow.pledges.get_by_id(pledge_id, event_id)
    if not pledge:
        return _response(404, {"error": "Pledge not found"})
    if str(pledge["member_id"]) != str(member["id"]):
        return _response(403, {"error": "This pledge does not belong to you"})
    if pledge["status"] == "cancelled":
        return _response(422, {"error": "Pledge is already cancelled"})

    if uow.pledges.has_contribution(pledge_id):
        return _response(422, {"error": "Cannot cancel a pledge that has already been paid for"})

    row = uow.pledges.cancel(pledge_id)
    return _response(200, serialize_pledge_cancel(row))


def record_contribution(uow, member: dict, event_id: str, body: dict) -> dict:
    err = _require_executive(member)
    if err:
        return err

    event = uow.events.get_by_id(event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot record contributions on a completed event"})

    amount = body.get("amount")
    received_at = body.get("received_at")
    if not amount or not received_at:
        return _response(422, {"error": "amount and received_at are required"})

    member_id = body.get("member_id")
    pledge_id = body.get("pledge_id")
    note = body.get("note")

    if member_id and not uow.members.get_by_id(member_id):
        return _response(404, {"error": "Member not found"})

    if pledge_id:
        pledge = uow.pledges.get_by_id_for_contribution(pledge_id, event_id)
        if not pledge:
            return _response(404, {"error": "Pledge not found"})
        if pledge["status"] == "cancelled":
            return _response(422, {"error": "Cannot record a contribution against a cancelled pledge"})

    row = uow.events.insert_contribution(event_id, member_id, pledge_id, amount,
                                         str(member["id"]), received_at, note)
    return _response(201, serialize_contribution_insert(row))
