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
    "quantity_remaining": 7, "is_available": True, "created_at": "2026-04-05T10:00:00",
}

PLEDGE = {
    "id": "pledge-uuid", "event_id": "event-uuid", "member_id": "member-uuid",
    "event_item_id": "item-uuid", "item_name": "Crates of Coke",
    "quantity": 3, "status": "pledged", "created_at": "2026-04-05T10:00:00",
    "updated_at": "2026-04-05T10:00:00",
}


def _make_uow(caller=EXEC_MEMBER, event=UPCOMING_EVENT, items=None, pledges=None,
              contributions=None, existing_pledge=None, quantity_remaining=7.0,
              pledge_row=None, has_contribution=False, has_items_or_pledges=False,
              has_contributions=False):
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.members.get_by_cognito_sub.return_value = caller
    uow.members.get_by_id.return_value = {"id": "member-uuid"}
    uow.events.get_by_id.return_value = event
    uow.events.get_all.return_value = [event] if event else []
    uow.events.get_items.return_value = items or [EVENT_ITEM]
    uow.events.get_pledges.return_value = pledges or []
    uow.events.get_contributions.return_value = contributions or []
    uow.events.insert.return_value = event
    uow.events.update.return_value = event
    uow.events.insert_items.return_value = [EVENT_ITEM]
    uow.events.insert_contribution.return_value = {
        "id": "contrib-uuid", "event_id": "event-uuid", "member_id": "member-uuid",
        "pledge_id": None, "amount": 50.0, "received_at": "2026-04-05T10:00:00",
        "note": None, "created_at": "2026-04-05T10:00:00",
    }
    uow.events.has_items_or_pledges.return_value = has_items_or_pledges
    uow.events.has_contributions.return_value = has_contributions
    uow.pledges.get_item_by_id.return_value = EVENT_ITEM
    uow.pledges.get_existing.return_value = existing_pledge
    uow.pledges.get_quantity_remaining.return_value = quantity_remaining
    uow.pledges.insert.return_value = PLEDGE
    uow.pledges.get_by_id.return_value = pledge_row or PLEDGE
    uow.pledges.get_by_id_for_contribution.return_value = pledge_row or PLEDGE
    uow.pledges.update_quantity.return_value = PLEDGE
    uow.pledges.cancel.return_value = {"id": "pledge-uuid", "status": "cancelled", "updated_at": "2026-04-05"}
    uow.pledges.has_contribution.return_value = has_contribution
    return uow


def _event(route_key, body=None, path_params=None, cognito_sub="exec-sub"):
    return generate_api_gw_event(body, cognito_sub=cognito_sub, route_key=route_key,
                                 path_params=path_params)


# ── POST /events ──────────────────────────────────────────────────────────────

@patch("functions.events.events.EventUoW")
def test_create_event_returns_201(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = events.handler(_event("POST /v1/events", {"title": "T", "date": "2026-08-12", "type": "pledge"}), generate_context())
    assert result["statusCode"] == 201


@patch("functions.events.events.EventUoW")
def test_create_event_requires_executive(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER)
    result = events.handler(_event("POST /v1/events", {"title": "T", "date": "2026-08-12", "type": "pledge"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.events.events.EventUoW")
def test_create_event_invalid_type_returns_422(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = events.handler(_event("POST /v1/events", {"title": "T", "date": "2026-08-12", "type": "invalid"}), generate_context())
    assert result["statusCode"] == 422


# ── GET /events ───────────────────────────────────────────────────────────────

@patch("functions.events.events.EventUoW")
def test_list_events_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = events.handler(_event("GET /v1/events"), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert len(body["events"]) == 1


# ── GET /events/{id} ──────────────────────────────────────────────────────────

@patch("functions.events.events.EventUoW")
def test_get_event_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = events.handler(_event("GET /v1/events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert "items" in body


@patch("functions.events.events.EventUoW")
def test_get_event_not_found_returns_404(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(event=None)
    result = events.handler(_event("GET /v1/events/{id}", path_params={"id": "bad-uuid"}), generate_context())
    assert result["statusCode"] == 404


# ── POST /events/{id}/items ───────────────────────────────────────────────────

@patch("functions.events.events.EventUoW")
def test_add_items_returns_201(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    body = {"items": [{"name": "Coke", "quantity_needed": 10, "unit": "crates"}]}
    result = events.handler(_event("POST /v1/events/{id}/items", body, {"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 201


@patch("functions.events.events.EventUoW")
def test_add_items_requires_executive(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER)
    body = {"items": [{"name": "Coke", "quantity_needed": 10, "unit": "crates"}]}
    result = events.handler(_event("POST /v1/events/{id}/items", body, {"id": "event-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 403


# ── POST /events/{id}/pledges ─────────────────────────────────────────────────

@patch("functions.events.events.EventUoW")
def test_create_pledge_returns_201(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER)
    body = {"event_item_id": "item-uuid", "quantity": 5}
    result = events.handler(_event("POST /v1/events/{id}/pledges", body, {"id": "event-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 201


@patch("functions.events.events.EventUoW")
def test_create_pledge_duplicate_returns_409(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER, existing_pledge=PLEDGE)
    body = {"event_item_id": "item-uuid", "quantity": 5}
    result = events.handler(_event("POST /v1/events/{id}/pledges", body, {"id": "event-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 409


@patch("functions.events.events.EventUoW")
def test_create_pledge_exceeds_remaining_returns_422(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER, quantity_remaining=3.0)
    body = {"event_item_id": "item-uuid", "quantity": 5}
    result = events.handler(_event("POST /v1/events/{id}/pledges", body, {"id": "event-uuid"}, cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 422


# ── DELETE /events/{id}/pledges/{pledgeId} ────────────────────────────────────

@patch("functions.events.events.EventUoW")
def test_cancel_pledge_returns_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER)
    result = events.handler(_event("DELETE /v1/events/{id}/pledges/{pledgeId}",
                                   path_params={"id": "event-uuid", "pledgeId": "pledge-uuid"},
                                   cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 200


@patch("functions.events.events.EventUoW")
def test_cancel_pledge_with_contribution_returns_422(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER, has_contribution=True)
    result = events.handler(_event("DELETE /v1/events/{id}/pledges/{pledgeId}",
                                   path_params={"id": "event-uuid", "pledgeId": "pledge-uuid"},
                                   cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 422


# ── DELETE /event-contributions/{id} ──────────────────────────────────────────

CONTRIBUTION = {"id": "contrib-uuid"}


def _make_uow_contrib(caller=EXEC_MEMBER, contribution=CONTRIBUTION):
    uow = _make_uow(caller=caller)
    uow.events.get_contribution_by_id.return_value = contribution
    return uow


@patch("functions.events.events.EventUoW")
def test_delete_contribution_returns_204(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow_contrib()
    result = events.handler(_event("DELETE /v1/event-contributions/{id}",
                                   path_params={"id": "contrib-uuid"}), generate_context())
    assert result["statusCode"] == 204


@patch("functions.events.events.EventUoW")
def test_delete_contribution_requires_executive(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow_contrib(caller=REGULAR_MEMBER)
    result = events.handler(_event("DELETE /v1/event-contributions/{id}",
                                   path_params={"id": "contrib-uuid"},
                                   cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 403


@patch("functions.events.events.EventUoW")
def test_delete_contribution_not_found_returns_404(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow_contrib(contribution=None)
    result = events.handler(_event("DELETE /v1/event-contributions/{id}",
                                   path_params={"id": "contrib-uuid"}), generate_context())
    assert result["statusCode"] == 404


# ── DELETE /events/{id} ───────────────────────────────────────────────────────

CONTRIBUTION_EVENT = {**UPCOMING_EVENT, "type": "contribution"}
GENERAL_EVENT = {**UPCOMING_EVENT, "type": "general"}
COMPLETED_EVENT = {**UPCOMING_EVENT, "status": "completed"}


@patch("functions.events.events.EventUoW")
def test_delete_event_returns_204(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(event=GENERAL_EVENT)
    result = events.handler(_event("DELETE /v1/events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 204


@patch("functions.events.events.EventUoW")
def test_delete_event_requires_executive(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER, event=GENERAL_EVENT)
    result = events.handler(_event("DELETE /v1/events/{id}", path_params={"id": "event-uuid"},
                                   cognito_sub="member-sub"), generate_context())
    assert result["statusCode"] == 403


@patch("functions.events.events.EventUoW")
def test_delete_event_not_found_returns_404(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(event=None)
    result = events.handler(_event("DELETE /v1/events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 404


@patch("functions.events.events.EventUoW")
def test_delete_completed_event_returns_422(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(event=COMPLETED_EVENT)
    result = events.handler(_event("DELETE /v1/events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.events.events.EventUoW")
def test_delete_pledge_event_with_items_returns_422(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(has_items_or_pledges=True)
    result = events.handler(_event("DELETE /v1/events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.events.events.EventUoW")
def test_delete_pledge_event_with_contributions_returns_422(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(has_contributions=True)
    result = events.handler(_event("DELETE /v1/events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.events.events.EventUoW")
def test_delete_contribution_event_with_contributions_returns_422(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(event=CONTRIBUTION_EVENT, has_contributions=True)
    result = events.handler(_event("DELETE /v1/events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.events.events.EventUoW")
def test_delete_general_event_ignores_data_checks(mock_uow_cls):
    # general events can be deleted even if has_items_or_pledges/has_contributions would be true
    mock_uow_cls.return_value = _make_uow(event=GENERAL_EVENT, has_items_or_pledges=True, has_contributions=True)
    result = events.handler(_event("DELETE /v1/events/{id}", path_params={"id": "event-uuid"}), generate_context())
    assert result["statusCode"] == 204
