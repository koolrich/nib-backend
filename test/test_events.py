import json
from unittest.mock import patch, MagicMock
import functions.events.events as events
from utils import generate_context, generate_api_gw_event

EXEC_MEMBER = {"id": "exec-uuid", "member_role": "executive"}
REGULAR_MEMBER = {"id": "member-uuid", "member_role": "member"}

UPCOMING_EVENT = {
    "id": "event-uuid", "title": "Test Event", "date": "2026-08-12",
    "type": "pledge", "status": "upcoming", "description": None,
    "created_by": "exec-uuid", "created_at": "2026-04-05T10:00:00",
    "total_contributions": 0, "total_pledges": 0,
}

EVENT_ITEM = {
    "id": "item-uuid", "event_id": "event-uuid", "name": "Crates of Coke",
    "quantity_needed": 10, "unit": "crates", "quantity_pledged": 3,
    "quantity_remaining": 7, "is_available": True,
}

PLEDGE = {
    "id": "pledge-uuid", "event_id": "event-uuid", "member_id": "member-uuid",
    "event_item_id": "item-uuid", "item_name": "Crates of Coke",
    "quantity": 3, "status": "pledged", "updated_at": "2026-04-05T10:00:00",
}


def _event(route_key, body=None, path_params=None, cognito_sub="exec-sub"):
    ev = generate_api_gw_event(body, cognito_sub=cognito_sub)
    ev["routeKey"] = route_key
    if path_params:
        ev["pathParameters"] = path_params
    return ev


# ── POST /events ──────────────────────────────────────────────────────────────

@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.events.events.insert_event", return_value=UPCOMING_EVENT)
def test_create_event_returns_201(mock_insert, mock_ctx, mock_conn):
    result = events.handler(_event("POST /events", {"title": "T", "date": "2026-08-12", "type": "pledge"}), generate_context())
    assert result["statusCode"] == 201
    mock_insert.assert_called_once()


@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=REGULAR_MEMBER)
def test_create_event_requires_executive(mock_ctx, mock_conn):
    result = events.handler(_event("POST /events", {"title": "T", "date": "2026-08-12", "type": "pledge"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=EXEC_MEMBER)
def test_create_event_invalid_type_returns_422(mock_ctx, mock_conn):
    result = events.handler(_event("POST /events", {"title": "T", "date": "2026-08-12", "type": "invalid"}), generate_context())
    assert result["statusCode"] == 422


# ── GET /events ───────────────────────────────────────────────────────────────

@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.events.events.get_events", return_value=[UPCOMING_EVENT])
def test_list_events_returns_200(mock_get, mock_ctx, mock_conn):
    result = events.handler(_event("GET /events"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["events"]) == 1


# ── GET /events/{id} ──────────────────────────────────────────────────────────

@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=UPCOMING_EVENT)
@patch("functions.events.events.get_event_items", return_value=[EVENT_ITEM])
@patch("functions.events.events.get_event_pledges", return_value=[])
@patch("functions.events.events.get_event_contributions", return_value=[])
def test_get_event_returns_200(mock_contrib, mock_pledges, mock_items, mock_event, mock_ctx, mock_conn):
    result = events.handler(_event("GET /events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "items" in body


@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=None)
def test_get_event_not_found_returns_404(mock_event, mock_ctx, mock_conn):
    result = events.handler(_event("GET /events/{id}", path_params={"id": "bad-uuid"}), generate_context())
    assert result["statusCode"] == 404


# ── POST /events/{id}/items ───────────────────────────────────────────────────

@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=UPCOMING_EVENT)
@patch("functions.events.events.insert_event_items", return_value=[EVENT_ITEM])
def test_add_items_returns_201(mock_insert, mock_event, mock_ctx, mock_conn):
    body = {"items": [{"name": "Coke", "quantity_needed": 10, "unit": "crates"}]}
    result = events.handler(_event("POST /events/{id}/items", body, {"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 201


@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=REGULAR_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=UPCOMING_EVENT)
def test_add_items_requires_executive(mock_event, mock_ctx, mock_conn):
    body = {"items": [{"name": "Coke", "quantity_needed": 10, "unit": "crates"}]}
    result = events.handler(_event("POST /events/{id}/items", body, {"id": "event-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 403


# ── POST /events/{id}/pledges ─────────────────────────────────────────────────

@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=REGULAR_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=UPCOMING_EVENT)
@patch("functions.events.events.get_event_item_by_id", return_value=EVENT_ITEM)
@patch("functions.events.events.get_existing_pledge", return_value=None)
@patch("functions.events.events.get_quantity_remaining", return_value=7.0)
@patch("functions.events.events.insert_pledge", return_value=PLEDGE)
def test_create_pledge_returns_201(mock_insert, mock_remaining, mock_existing, mock_item, mock_event, mock_ctx, mock_conn):
    body = {"event_item_id": "item-uuid", "quantity": 5}
    result = events.handler(_event("POST /events/{id}/pledges", body, {"id": "event-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 201


@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=REGULAR_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=UPCOMING_EVENT)
@patch("functions.events.events.get_event_item_by_id", return_value=EVENT_ITEM)
@patch("functions.events.events.get_existing_pledge", return_value=PLEDGE)
def test_create_pledge_duplicate_returns_409(mock_existing, mock_item, mock_event, mock_ctx, mock_conn):
    body = {"event_item_id": "item-uuid", "quantity": 5}
    result = events.handler(_event("POST /events/{id}/pledges", body, {"id": "event-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 409


@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=REGULAR_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=UPCOMING_EVENT)
@patch("functions.events.events.get_event_item_by_id", return_value=EVENT_ITEM)
@patch("functions.events.events.get_existing_pledge", return_value=None)
@patch("functions.events.events.get_quantity_remaining", return_value=3.0)
def test_create_pledge_exceeds_remaining_returns_422(mock_remaining, mock_existing, mock_item, mock_event, mock_ctx, mock_conn):
    body = {"event_item_id": "item-uuid", "quantity": 5}
    result = events.handler(_event("POST /events/{id}/pledges", body, {"id": "event-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 422


# ── DELETE /events/{id}/pledges/{pledgeId} ────────────────────────────────────

@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=REGULAR_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=UPCOMING_EVENT)
@patch("functions.events.events.get_pledge_by_id", return_value=PLEDGE)
@patch("functions.events.events.pledge_has_contribution", return_value=False)
@patch("functions.events.events.cancel_pledge", return_value={"id": "pledge-uuid", "status": "cancelled", "updated_at": "2026-04-05"})
def test_cancel_pledge_returns_200(mock_cancel, mock_contrib, mock_pledge, mock_event, mock_ctx, mock_conn):
    result = events.handler(_event("DELETE /events/{id}/pledges/{pledgeId}", path_params={"id": "event-uuid", "pledgeId": "pledge-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 200


@patch("functions.events.events.get_connection")
@patch("functions.events.events.get_member_context", return_value=REGULAR_MEMBER)
@patch("functions.events.events.get_event_by_id", return_value=UPCOMING_EVENT)
@patch("functions.events.events.get_pledge_by_id", return_value=PLEDGE)
@patch("functions.events.events.pledge_has_contribution", return_value=True)
def test_cancel_pledge_with_contribution_returns_422(mock_contrib, mock_pledge, mock_event, mock_ctx, mock_conn):
    result = events.handler(_event("DELETE /events/{id}/pledges/{pledgeId}", path_params={"id": "event-uuid", "pledgeId": "pledge-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 422
