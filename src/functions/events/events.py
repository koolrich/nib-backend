import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.db import get_connection
from shared.instrumentation.tracer import tracer
from shared.services.member_service import get_member_context
from shared.services.event_service import (
    insert_event,
    get_events,
    get_event_by_id,
    get_event_items,
    get_event_pledges,
    get_event_contributions,
    update_event,
    event_has_items_or_pledges,
    insert_event_items,
    insert_contribution,
    get_member_by_id,
)
from shared.services.pledge_service import (
    get_event_item_by_id,
    get_existing_pledge,
    get_quantity_remaining,
    insert_pledge,
    get_pledge_by_id,
    update_pledge_quantity,
    cancel_pledge,
    pledge_has_contribution,
    get_pledge_by_id_for_contribution,
)

logger = Logger()

VALID_EVENT_TYPES = {"pledge", "contribution"}
VALID_EVENT_STATUSES = {"upcoming", "completed"}


def _response(status_code: int, body: dict) -> dict:
    return {"statusCode": status_code, "body": json.dumps(body, default=str)}


def _get_cognito_sub(event: dict) -> str:
    return event["requestContext"]["authorizer"]["jwt"]["claims"]["sub"]


def _require_executive(member: dict) -> dict | None:
    if member["member_role"] != "executive" and member["member_role"] != "admin":
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

        # POST /events
        if route_key == "POST /events":
            return _create_event(conn, member, body)

        # GET /events
        if route_key == "GET /events":
            return _list_events(conn)

        # GET /events/{id}
        if route_key == "GET /events/{id}":
            return _get_event(conn, path_params["id"])

        # PATCH /events/{id}
        if route_key == "PATCH /events/{id}":
            return _patch_event(conn, member, path_params["id"], body)

        # POST /events/{id}/items
        if route_key == "POST /events/{id}/items":
            return _add_items(conn, member, path_params["id"], body)

        # POST /events/{id}/pledges
        if route_key == "POST /events/{id}/pledges":
            return _create_pledge(conn, member, path_params["id"], body)

        # PATCH /events/{id}/pledges/{pledgeId}
        if route_key == "PATCH /events/{id}/pledges/{pledgeId}":
            return _update_pledge(conn, member, path_params["id"], path_params["pledgeId"], body)

        # DELETE /events/{id}/pledges/{pledgeId}
        if route_key == "DELETE /events/{id}/pledges/{pledgeId}":
            return _cancel_pledge(conn, member, path_params["id"], path_params["pledgeId"])

        # POST /events/{id}/contributions
        if route_key == "POST /events/{id}/contributions":
            return _record_contribution(conn, member, path_params["id"], body)

        return _response(404, {"error": "Route not found"})

    except Exception as e:
        if conn:
            conn.rollback()
        logger.exception("Unexpected error", extra={"error": str(e)})
        return _response(500, {"error": str(e)})

    finally:
        if conn:
            conn.close()


def _create_event(conn, member, body):
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

    row = insert_event(conn, title, date, type_, description, str(member["id"]))
    conn.commit()
    return _response(201, dict(row))


def _list_events(conn):
    rows = get_events(conn)
    return _response(200, {"events": [dict(r) for r in rows]})


def _get_event(conn, event_id):
    event = get_event_by_id(conn, event_id)
    if not event:
        return _response(404, {"error": "Event not found"})

    result = dict(event)
    if event["type"] == "pledge":
        result["items"] = [dict(i) for i in get_event_items(conn, event_id)]
    result["pledges"] = [dict(p) for p in get_event_pledges(conn, event_id)]
    result["contributions"] = [dict(c) for c in get_event_contributions(conn, event_id)]
    return _response(200, result)


def _patch_event(conn, member, event_id, body):
    err = _require_executive(member)
    if err:
        return err

    event = get_event_by_id(conn, event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot edit a completed event"})

    if "type" in body and body["type"] != event["type"]:
        if event_has_items_or_pledges(conn, event_id):
            return _response(422, {"error": "Cannot change event type after items or pledges have been added"})

    if "status" in body and body["status"] not in VALID_EVENT_STATUSES:
        return _response(422, {"error": f"status must be one of: {', '.join(VALID_EVENT_STATUSES)}"})

    if "type" in body and body["type"] not in VALID_EVENT_TYPES:
        return _response(422, {"error": f"type must be one of: {', '.join(VALID_EVENT_TYPES)}"})

    row = update_event(conn, event_id, body)
    conn.commit()
    return _response(200, dict(row))


def _add_items(conn, member, event_id, body):
    err = _require_executive(member)
    if err:
        return err

    event = get_event_by_id(conn, event_id)
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

    rows = insert_event_items(conn, event_id, items)
    conn.commit()
    return _response(201, {"items": [dict(r) for r in rows]})


def _create_pledge(conn, member, event_id, body):
    event = get_event_by_id(conn, event_id)
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

    item = get_event_item_by_id(conn, event_item_id, event_id)
    if not item:
        return _response(404, {"error": "Event item not found"})

    member_id = str(member["id"])
    existing = get_existing_pledge(conn, member_id, event_item_id)
    if existing:
        return _response(409, {"error": "You have an existing pledge for this item, please edit it instead"})

    remaining = get_quantity_remaining(conn, event_item_id)
    if remaining <= 0:
        return _response(422, {"error": "This item has been fully pledged"})
    if quantity > remaining:
        return _response(422, {"error": f"Only {remaining} units remaining"})

    row = insert_pledge(conn, event_id, member_id, event_item_id, quantity)
    conn.commit()
    return _response(201, dict(row))


def _update_pledge(conn, member, event_id, pledge_id, body):
    event = get_event_by_id(conn, event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot edit a pledge on a completed event"})

    pledge = get_pledge_by_id(conn, pledge_id, event_id)
    if not pledge:
        return _response(404, {"error": "Pledge not found"})
    if str(pledge["member_id"]) != str(member["id"]):
        return _response(403, {"error": "This pledge does not belong to you"})
    if pledge["status"] == "cancelled":
        return _response(422, {"error": "Cannot edit a cancelled pledge"})

    quantity = body.get("quantity")
    if not quantity:
        return _response(422, {"error": "quantity is required"})

    remaining = get_quantity_remaining(conn, str(pledge["event_item_id"]), str(member["id"]))
    if quantity > remaining:
        return _response(422, {"error": f"Only {remaining} units remaining"})

    row = update_pledge_quantity(conn, pledge_id, quantity)
    conn.commit()
    return _response(200, dict(row))


def _cancel_pledge(conn, member, event_id, pledge_id):
    event = get_event_by_id(conn, event_id)
    if not event:
        return _response(404, {"error": "Event not found"})
    if event["status"] == "completed":
        return _response(422, {"error": "Cannot cancel a pledge on a completed event"})

    pledge = get_pledge_by_id(conn, pledge_id, event_id)
    if not pledge:
        return _response(404, {"error": "Pledge not found"})
    if str(pledge["member_id"]) != str(member["id"]):
        return _response(403, {"error": "This pledge does not belong to you"})
    if pledge["status"] == "cancelled":
        return _response(422, {"error": "Pledge is already cancelled"})

    if pledge_has_contribution(conn, pledge_id):
        return _response(422, {"error": "Cannot cancel a pledge that has already been paid for"})

    row = cancel_pledge(conn, pledge_id)
    conn.commit()
    return _response(200, dict(row))


def _record_contribution(conn, member, event_id, body):
    err = _require_executive(member)
    if err:
        return err

    event = get_event_by_id(conn, event_id)
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

    if member_id:
        if not get_member_by_id(conn, member_id):
            return _response(404, {"error": "Member not found"})

    if pledge_id:
        pledge = get_pledge_by_id_for_contribution(conn, pledge_id, event_id)
        if not pledge:
            return _response(404, {"error": "Pledge not found"})
        if pledge["status"] == "cancelled":
            return _response(422, {"error": "Cannot record a contribution against a cancelled pledge"})

    row = insert_contribution(conn, event_id, member_id, pledge_id, amount,
                              str(member["id"]), received_at, note)
    conn.commit()
    return _response(201, dict(row))
