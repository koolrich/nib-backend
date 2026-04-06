from unittest.mock import patch, MagicMock
from decimal import Decimal
import functions.payments.payments as payments
from utils import generate_context, generate_api_gw_event

EXEC_MEMBER = {"id": "exec-uuid-1234", "member_role": "executive"}
REGULAR_MEMBER = {"id": "member-uuid-1234", "member_role": "member"}

UNPAID_INVOICE = {
    "id": "invoice-uuid-1234",
    "membership_period_id": "period-uuid-1234",
    "invoice_number": "NIB-0001",
    "issue_date": "2026-01-01",
    "due_date": "2026-02-01",
    "amount_due": Decimal("60.00"),
    "status": "unpaid",
    "created_at": "2026-01-01T00:00:00",
}

PAID_INVOICE = {**UNPAID_INVOICE, "status": "paid"}

PAYMENT_ROW = {
    "id": "payment-uuid-1234",
    "invoice_id": "invoice-uuid-1234",
    "amount": Decimal("25.00"),
    "method": "bank_transfer",
    "reference": "REF123",
    "received_by": "exec-uuid-1234",
    "received_at": "2026-02-01T10:00:00Z",
    "note": "Monthly instalment",
    "created_at": "2026-04-07T00:00:00",
}

VALID_PAYMENT_BODY = {
    "amount": 25.00,
    "method": "bank_transfer",
    "reference": "REF123",
    "received_at": "2026-02-01T10:00:00Z",
    "note": "Monthly instalment",
}

MEMBER_INFO = {
    "id": "member-uuid-1234",
    "is_legacy": False,
    "membership_id": "membership-uuid-1234",
    "membership_type": "individual",
}

PERIOD_ROW = {
    "id": "period-uuid-1234",
    "membership_id": "membership-uuid-1234",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "status": "active",
    "created_at": "2026-01-01T00:00:00",
}


# --- POST /invoices/{id}/payments ---

@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_invoice_by_id", return_value=UNPAID_INVOICE)
@patch("functions.payments.payments.get_total_paid", return_value=Decimal("0.00"))
@patch("functions.payments.payments.insert_payment", return_value=PAYMENT_ROW)
@patch("functions.payments.payments.update_invoice_status")
def test_record_payment_201_partial(mock_update, mock_insert, mock_total,
                                    mock_invoice, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event(VALID_PAYMENT_BODY, route_key="POST /invoices/{id}/payments",
                              path_params={"id": "invoice-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 201
    import json
    body = json.loads(result["body"])
    assert body["invoice"]["status"] == "partial"
    assert body["invoice"]["outstanding"] == 35.0


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_invoice_by_id", return_value=UNPAID_INVOICE)
@patch("functions.payments.payments.get_total_paid", return_value=Decimal("0.00"))
@patch("functions.payments.payments.insert_payment", return_value={**PAYMENT_ROW, "amount": Decimal("60.00")})
@patch("functions.payments.payments.update_invoice_status")
def test_record_payment_201_paid(mock_update, mock_insert, mock_total,
                                 mock_invoice, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({**VALID_PAYMENT_BODY, "amount": 60.00},
                              route_key="POST /invoices/{id}/payments",
                              path_params={"id": "invoice-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 201
    import json
    body = json.loads(result["body"])
    assert body["invoice"]["status"] == "paid"
    assert body["invoice"]["outstanding"] == 0.0


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=REGULAR_MEMBER)
def test_record_payment_403_not_exec(mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event(VALID_PAYMENT_BODY, route_key="POST /invoices/{id}/payments",
                              path_params={"id": "invoice-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 403


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_invoice_by_id", return_value=None)
def test_record_payment_404_invoice_not_found(mock_invoice, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event(VALID_PAYMENT_BODY, route_key="POST /invoices/{id}/payments",
                              path_params={"id": "nonexistent"}),
        generate_context(),
    )
    assert result["statusCode"] == 404


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_invoice_by_id", return_value=PAID_INVOICE)
def test_record_payment_422_invoice_paid(mock_invoice, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event(VALID_PAYMENT_BODY, route_key="POST /invoices/{id}/payments",
                              path_params={"id": "invoice-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 422


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_invoice_by_id", return_value=UNPAID_INVOICE)
@patch("functions.payments.payments.get_total_paid", return_value=Decimal("0.00"))
def test_record_payment_422_exceeds_balance(mock_total, mock_invoice, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({**VALID_PAYMENT_BODY, "amount": 999.00},
                              route_key="POST /invoices/{id}/payments",
                              path_params={"id": "invoice-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 422


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_invoice_by_id", return_value=UNPAID_INVOICE)
@patch("functions.payments.payments.get_total_paid", return_value=Decimal("0.00"))
def test_record_payment_422_invalid_method(mock_total, mock_invoice, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({**VALID_PAYMENT_BODY, "method": "crypto"},
                              route_key="POST /invoices/{id}/payments",
                              path_params={"id": "invoice-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 422


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_invoice_by_id", return_value=UNPAID_INVOICE)
@patch("functions.payments.payments.get_total_paid", return_value=Decimal("0.00"))
def test_record_payment_422_missing_fields(mock_total, mock_invoice, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({"amount": 25.00}, route_key="POST /invoices/{id}/payments",
                              path_params={"id": "invoice-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 422


# --- DELETE /payments/{id} ---

@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_payment_by_id", return_value=PAYMENT_ROW)
@patch("functions.payments.payments.delete_payment")
@patch("functions.payments.payments.get_total_paid", return_value=Decimal("0.00"))
@patch("functions.payments.payments.get_invoice_by_id", return_value=UNPAID_INVOICE)
@patch("functions.payments.payments.update_invoice_status")
def test_delete_payment_200_resets_to_unpaid(mock_update, mock_invoice, mock_total,
                                              mock_delete, mock_get, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event(None, route_key="DELETE /payments/{id}",
                              path_params={"id": "payment-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 200
    import json
    body = json.loads(result["body"])
    assert body["invoice_status"] == "unpaid"
    mock_update.assert_called_once_with(mock_db, "invoice-uuid-1234", "unpaid")


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=REGULAR_MEMBER)
def test_delete_payment_403_not_exec(mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event(None, route_key="DELETE /payments/{id}",
                              path_params={"id": "payment-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 403


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_payment_by_id", return_value=None)
def test_delete_payment_404_not_found(mock_get, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event(None, route_key="DELETE /payments/{id}",
                              path_params={"id": "nonexistent"}),
        generate_context(),
    )
    assert result["statusCode"] == 404


# --- GET /members/{id}/statement ---

@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_member_by_id", return_value={"id": "member-uuid-1234", "membership_id": "membership-uuid-1234", "is_legacy": False})
@patch("functions.payments.payments.get_member_with_membership_type", return_value=MEMBER_INFO)
@patch("functions.payments.payments.get_active_period_for_membership", return_value=PERIOD_ROW)
@patch("functions.payments.payments.get_invoice_by_period_id", return_value=UNPAID_INVOICE)
@patch("functions.payments.payments.get_payments_by_invoice", return_value=[])
def test_get_statement_200_no_payments(mock_pmts, mock_invoice, mock_period, mock_info,
                                       mock_member, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({}, route_key="GET /members/{id}/statement",
                              path_params={"id": "member-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 200
    import json
    body = json.loads(result["body"])
    assert body["invoice"]["outstanding"] == 60.0
    assert body["payments"] == []


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=REGULAR_MEMBER)
@patch("functions.payments.payments.get_member_by_id", return_value={"id": "member-uuid-1234", "membership_id": "membership-uuid-1234", "is_legacy": False})
@patch("functions.payments.payments.get_member_with_membership_type", return_value=MEMBER_INFO)
@patch("functions.payments.payments.get_active_period_for_membership", return_value=PERIOD_ROW)
@patch("functions.payments.payments.get_invoice_by_period_id", return_value=UNPAID_INVOICE)
@patch("functions.payments.payments.get_payments_by_invoice", return_value=[])
def test_get_statement_200_own_statement(mock_pmts, mock_invoice, mock_period, mock_info,
                                         mock_member, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({}, route_key="GET /members/{id}/statement",
                              path_params={"id": "member-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 200


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=REGULAR_MEMBER)
@patch("functions.payments.payments.get_member_by_id", return_value={"id": "other-member-uuid", "membership_id": "membership-uuid-1234", "is_legacy": False})
def test_get_statement_403_other_member(mock_member, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({}, route_key="GET /members/{id}/statement",
                              path_params={"id": "other-member-uuid"}),
        generate_context(),
    )
    assert result["statusCode"] == 403


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_member_by_id", return_value=None)
def test_get_statement_404_member_not_found(mock_member, mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({}, route_key="GET /members/{id}/statement",
                              path_params={"id": "nonexistent"}),
        generate_context(),
    )
    assert result["statusCode"] == 404


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_member_by_id", return_value={"id": "member-uuid-1234", "membership_id": "membership-uuid-1234", "is_legacy": True})
@patch("functions.payments.payments.get_member_with_membership_type", return_value=MEMBER_INFO)
@patch("functions.payments.payments.get_active_period_for_membership", return_value=None)
def test_get_statement_200_no_active_period(mock_period, mock_info, mock_member,
                                            mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({}, route_key="GET /members/{id}/statement",
                              path_params={"id": "member-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 200
    import json
    body = json.loads(result["body"])
    assert body["period"] is None
    assert body["invoice"] is None


@patch("functions.payments.payments.get_connection")
@patch("functions.payments.payments.get_member_context", return_value=EXEC_MEMBER)
@patch("functions.payments.payments.get_member_by_id", return_value={"id": "member-uuid-1234", "membership_id": "membership-uuid-1234", "is_legacy": True})
@patch("functions.payments.payments.get_member_with_membership_type", return_value=MEMBER_INFO)
@patch("functions.payments.payments.get_active_period_for_membership", return_value=PERIOD_ROW)
@patch("functions.payments.payments.get_invoice_by_period_id", return_value=None)
def test_get_statement_200_no_invoice(mock_invoice, mock_period, mock_info, mock_member,
                                      mock_ctx, mock_conn, mock_db):
    mock_conn.return_value = mock_db
    result = payments.handler(
        generate_api_gw_event({}, route_key="GET /members/{id}/statement",
                              path_params={"id": "member-uuid-1234"}),
        generate_context(),
    )
    assert result["statusCode"] == 200
    import json
    body = json.loads(result["body"])
    assert body["period"] is not None
    assert body["invoice"] is None
