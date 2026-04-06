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

VALID_PERIOD_BODY = {"period_start": "2024-01-01", "period_end": "2024-12-31"}

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


def _make_mock_db(fetchone_side_effects):
    mock_db = MagicMock()
    cursor = MagicMock()
    cursor.__enter__ = lambda s: cursor
    cursor.__exit__ = MagicMock(return_value=False)
    cursor.fetchone.side_effect = fetchone_side_effects
    mock_db.cursor.return_value = cursor
    return mock_db


# --- POST /members/{id}/membership-periods ---

@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.memberships.memberships.get_member_with_membership_type", return_value=LEGACY_MEMBER)
@patch("functions.memberships.memberships.insert_membership_period", return_value=PERIOD_ROW)
@patch("functions.memberships.memberships.get_current_fee", return_value={"annual_fee": 60.00, "due_days": 30})
@patch("functions.memberships.memberships.generate_invoice_number", return_value="NIB-0001")
@patch("functions.memberships.memberships.insert_invoice")
@patch("functions.memberships.memberships.get_invoice_by_period_id", return_value=INVOICE_ROW)
def test_create_period_201(mock_invoice_fetch, mock_insert_invoice, mock_gen_num,
                           mock_fee, mock_period, mock_member_info, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event(VALID_PERIOD_BODY, route_key="POST /members/{id}/membership-periods",
                              path_params={"id": "legacy-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 201


@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=REGULAR_MEMBER)
def test_create_period_403_not_exec(mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event(VALID_PERIOD_BODY, route_key="POST /members/{id}/membership-periods",
                              path_params={"id": "legacy-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 403


@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.memberships.memberships.get_member_with_membership_type", return_value=None)
def test_create_period_404_member_not_found(mock_member_info, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event(VALID_PERIOD_BODY, route_key="POST /members/{id}/membership-periods",
                              path_params={"id": "nonexistent"}),
        generate_context(),
    )
    assert result["statusCode"] == 404


@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.memberships.memberships.get_member_with_membership_type", return_value=NON_LEGACY_MEMBER)
def test_create_period_422_not_legacy(mock_member_info, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event(VALID_PERIOD_BODY, route_key="POST /members/{id}/membership-periods",
                              path_params={"id": "non-legacy-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 422


@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.memberships.memberships.get_member_with_membership_type",
       return_value={**LEGACY_MEMBER, "membership_id": None})
def test_create_period_422_no_membership(mock_member_info, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event(VALID_PERIOD_BODY, route_key="POST /members/{id}/membership-periods",
                              path_params={"id": "legacy-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 422


@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.memberships.memberships.get_member_with_membership_type", return_value=LEGACY_MEMBER)
def test_create_period_422_missing_dates(mock_member_info, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event({"period_start": "2024-01-01"}, route_key="POST /members/{id}/membership-periods",
                              path_params={"id": "legacy-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 422


# --- PATCH /membership-periods/{id} ---

@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.memberships.memberships.get_membership_period", return_value=PERIOD_ROW)
@patch("functions.memberships.memberships.update_membership_period", return_value={**PERIOD_ROW, "status": "expired"})
def test_patch_period_200(mock_update, mock_get, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event({"status": "expired"}, route_key="PATCH /membership-periods/{id}",
                              path_params={"id": "period-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 200


@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=REGULAR_MEMBER)
def test_patch_period_403_not_exec(mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event({"status": "expired"}, route_key="PATCH /membership-periods/{id}",
                              path_params={"id": "period-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 403


@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.memberships.memberships.get_membership_period", return_value=None)
def test_patch_period_404(mock_get, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event({"status": "expired"}, route_key="PATCH /membership-periods/{id}",
                              path_params={"id": "nonexistent"}),
        generate_context(),
    )
    assert result["statusCode"] == 404


@patch("functions.memberships.memberships.get_connection")
@patch("functions.memberships.memberships.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.memberships.memberships.get_membership_period", return_value=PERIOD_ROW)
def test_patch_period_422_invalid_status(mock_get, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = memberships.handler(
        generate_api_gw_event({"status": "invalid"}, route_key="PATCH /membership-periods/{id}",
                              path_params={"id": "period-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 422
