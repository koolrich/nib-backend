from unittest.mock import patch, MagicMock
import functions.memberships.memberships as memberships
from utils import generate_context, generate_api_gw_event

EXEC_MEMBER = {"id": "exec-uuid-1234", "member_role": "executive"}
REGULAR_MEMBER = {"id": "member-uuid-1234", "member_role": "member"}

LEGACY_MEMBER = {
    "id": "legacy-uuid-1234",
    "is_legacy": True,
    "membership_id": "membership-uuid-1234",
    "membership_type": "individual",
}

NON_LEGACY_MEMBER = {
    "id": "non-legacy-uuid-1234",
    "is_legacy": False,
    "membership_id": "membership-uuid-1234",
    "membership_type": "individual",
}

PERIOD_ROW = {
    "id": "period-uuid-1234",
    "membership_id": "membership-uuid-1234",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "status": "active",
    "created_at": "2026-01-01T00:00:00",
}

INVOICE_ROW = {
    "id": "invoice-uuid-1234",
    "membership_period_id": "period-uuid-1234",
    "invoice_number": "NIB-0001",
    "issue_date": "2026-04-07",
    "due_date": "2026-05-07",
    "amount_due": 60.00,
    "status": "unpaid",
    "created_at": "2026-04-07T00:00:00",
}

VALID_PERIOD_BODY = {"period_start": "2024-01-01", "period_end": "2024-12-31"}


def _make_uow(caller=EXEC_MEMBER, target=LEGACY_MEMBER, period=PERIOD_ROW, invoice=INVOICE_ROW, updated_period=None):
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.members.get_by_cognito_sub.return_value = caller
    uow.members.get_with_membership_type.return_value = target
    uow.periods.insert.return_value = period
    uow.periods.get_by_id.return_value = period
    uow.periods.update.return_value = updated_period or {**PERIOD_ROW, "status": "expired"}
    uow.invoices.insert.return_value = invoice
    return uow


def _event(route_key, body=None, path_params=None):
    return generate_api_gw_event(body, route_key=route_key, path_params=path_params)


# ── POST /members/{id}/membership-periods ─────────────────────────────────────

@patch("functions.memberships.memberships.MembershipUoW")
def test_create_period_201(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = memberships.handler(_event("POST /members/{id}/membership-periods",
                                        VALID_PERIOD_BODY, {"id": "legacy-uuid-1234"}), generate_context())
    assert result["statusCode"] == 201


@patch("functions.memberships.memberships.MembershipUoW")
def test_create_period_403_not_exec(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER)
    result = memberships.handler(_event("POST /members/{id}/membership-periods",
                                        VALID_PERIOD_BODY, {"id": "legacy-uuid-1234"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.memberships.memberships.MembershipUoW")
def test_create_period_404_member_not_found(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(target=None)
    result = memberships.handler(_event("POST /members/{id}/membership-periods",
                                        VALID_PERIOD_BODY, {"id": "nonexistent"}), generate_context())
    assert result["statusCode"] == 404


@patch("functions.memberships.memberships.MembershipUoW")
def test_create_period_422_not_legacy(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(target=NON_LEGACY_MEMBER)
    result = memberships.handler(_event("POST /members/{id}/membership-periods",
                                        VALID_PERIOD_BODY, {"id": "non-legacy-uuid"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.memberships.memberships.MembershipUoW")
def test_create_period_422_no_membership(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(target={**LEGACY_MEMBER, "membership_id": None})
    result = memberships.handler(_event("POST /members/{id}/membership-periods",
                                        VALID_PERIOD_BODY, {"id": "legacy-uuid-1234"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.memberships.memberships.MembershipUoW")
def test_create_period_422_missing_dates(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = memberships.handler(_event("POST /members/{id}/membership-periods",
                                        {"period_start": "2024-01-01"}, {"id": "legacy-uuid-1234"}), generate_context())
    assert result["statusCode"] == 422


# ── PATCH /membership-periods/{id} ───────────────────────────────────────────

@patch("functions.memberships.memberships.MembershipUoW")
def test_patch_period_200(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = memberships.handler(_event("PATCH /membership-periods/{id}",
                                        {"status": "expired"}, {"id": "period-uuid-1234"}), generate_context())
    assert result["statusCode"] == 200


@patch("functions.memberships.memberships.MembershipUoW")
def test_patch_period_403_not_exec(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER)
    result = memberships.handler(_event("PATCH /membership-periods/{id}",
                                        {"status": "expired"}, {"id": "period-uuid-1234"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.memberships.memberships.MembershipUoW")
def test_patch_period_404(mock_uow_cls):
    uow = _make_uow()
    uow.periods.get_by_id.return_value = None
    mock_uow_cls.return_value = uow
    result = memberships.handler(_event("PATCH /membership-periods/{id}",
                                        {"status": "expired"}, {"id": "nonexistent"}), generate_context())
    assert result["statusCode"] == 404


@patch("functions.memberships.memberships.MembershipUoW")
def test_patch_period_422_invalid_status(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = memberships.handler(_event("PATCH /membership-periods/{id}",
                                        {"status": "invalid"}, {"id": "period-uuid-1234"}), generate_context())
    assert result["statusCode"] == 422
