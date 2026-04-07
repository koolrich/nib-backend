from unittest.mock import patch, MagicMock
from decimal import Decimal
import json
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

PERIOD_ROW = {
    "id": "period-uuid-1234",
    "membership_id": "membership-uuid-1234",
    "start_date": "2026-01-01",
    "end_date": "2026-12-31",
    "status": "active",
    "created_at": "2026-01-01T00:00:00",
}

MEMBER_INFO = {
    "id": "member-uuid-1234",
    "is_legacy": False,
    "membership_id": "membership-uuid-1234",
    "membership_type": "individual",
}

VALID_PAYMENT_BODY = {
    "amount": 25.00,
    "method": "bank_transfer",
    "reference": "REF123",
    "received_at": "2026-02-01T10:00:00Z",
    "note": "Monthly instalment",
}


def _make_uow(caller=EXEC_MEMBER, invoice=UNPAID_INVOICE, total_paid=Decimal("0.00"),
              payment_row=PAYMENT_ROW, payment_by_id=None, member_by_id=None,
              member_with_type=MEMBER_INFO, period=PERIOD_ROW, invoice_by_period=None,
              all_payments=None):
    uow = MagicMock()
    uow.__enter__ = MagicMock(return_value=uow)
    uow.__exit__ = MagicMock(return_value=False)
    uow.members.get_by_cognito_sub.return_value = caller
    uow.members.get_by_id.return_value = member_by_id or {"id": "member-uuid-1234", "membership_id": "membership-uuid-1234"}
    uow.members.get_with_membership_type.return_value = member_with_type
    uow.invoices.get_by_id.return_value = invoice
    uow.invoices.get_by_period_id.return_value = invoice_by_period or invoice
    uow.payments.get_total_by_invoice.return_value = total_paid
    uow.payments.insert.return_value = payment_row
    uow.payments.get_by_id.return_value = payment_by_id or PAYMENT_ROW
    uow.payments.get_all_by_invoice.return_value = all_payments or []
    uow.periods.get_active_for_membership.return_value = period
    return uow


def _event(route_key, body=None, path_params=None):
    return generate_api_gw_event(body, route_key=route_key, path_params=path_params)


# ── POST /invoices/{id}/payments ──────────────────────────────────────────────

@patch("functions.payments.payments.PaymentUoW")
def test_record_payment_201_partial(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = payments.handler(_event("POST /v1/invoices/{id}/payments", VALID_PAYMENT_BODY,
                                     {"id": "invoice-uuid-1234"}), generate_context())
    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["invoice"]["status"] == "partial"
    assert body["invoice"]["outstanding"] == 35.0


@patch("functions.payments.payments.PaymentUoW")
def test_record_payment_201_paid(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(
        payment_row={**PAYMENT_ROW, "amount": Decimal("60.00")}
    )
    result = payments.handler(_event("POST /v1/invoices/{id}/payments",
                                     {**VALID_PAYMENT_BODY, "amount": 60.00},
                                     {"id": "invoice-uuid-1234"}), generate_context())
    assert result["statusCode"] == 201
    body = json.loads(result["body"])
    assert body["invoice"]["status"] == "paid"
    assert body["invoice"]["outstanding"] == 0.0


@patch("functions.payments.payments.PaymentUoW")
def test_record_payment_403_not_exec(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER)
    result = payments.handler(_event("POST /v1/invoices/{id}/payments", VALID_PAYMENT_BODY,
                                     {"id": "invoice-uuid-1234"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.payments.payments.PaymentUoW")
def test_record_payment_404_invoice_not_found(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(invoice=None)
    result = payments.handler(_event("POST /v1/invoices/{id}/payments", VALID_PAYMENT_BODY,
                                     {"id": "nonexistent"}), generate_context())
    assert result["statusCode"] == 404


@patch("functions.payments.payments.PaymentUoW")
def test_record_payment_422_invoice_paid(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(invoice=PAID_INVOICE)
    result = payments.handler(_event("POST /v1/invoices/{id}/payments", VALID_PAYMENT_BODY,
                                     {"id": "invoice-uuid-1234"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.payments.payments.PaymentUoW")
def test_record_payment_422_exceeds_balance(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = payments.handler(_event("POST /v1/invoices/{id}/payments",
                                     {**VALID_PAYMENT_BODY, "amount": 999.00},
                                     {"id": "invoice-uuid-1234"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.payments.payments.PaymentUoW")
def test_record_payment_422_invalid_method(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = payments.handler(_event("POST /v1/invoices/{id}/payments",
                                     {**VALID_PAYMENT_BODY, "method": "crypto"},
                                     {"id": "invoice-uuid-1234"}), generate_context())
    assert result["statusCode"] == 422


@patch("functions.payments.payments.PaymentUoW")
def test_record_payment_422_missing_fields(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = payments.handler(_event("POST /v1/invoices/{id}/payments", {"amount": 25.00},
                                     {"id": "invoice-uuid-1234"}), generate_context())
    assert result["statusCode"] == 422


# ── DELETE /payments/{id} ─────────────────────────────────────────────────────

@patch("functions.payments.payments.PaymentUoW")
def test_delete_payment_200_resets_to_unpaid(mock_uow_cls):
    uow = _make_uow(total_paid=Decimal("0.00"))
    mock_uow_cls.return_value = uow
    result = payments.handler(_event("DELETE /v1/payments/{id}", None,
                                     {"id": "payment-uuid-1234"}), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["invoice_status"] == "unpaid"


@patch("functions.payments.payments.PaymentUoW")
def test_delete_payment_403_not_exec(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER)
    result = payments.handler(_event("DELETE /v1/payments/{id}", None,
                                     {"id": "payment-uuid-1234"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.payments.payments.PaymentUoW")
def test_delete_payment_404_not_found(mock_uow_cls):
    uow = _make_uow()
    uow.payments.get_by_id.return_value = None
    mock_uow_cls.return_value = uow
    result = payments.handler(_event("DELETE /v1/payments/{id}", None,
                                     {"id": "nonexistent"}), generate_context())
    assert result["statusCode"] == 404


# ── GET /members/{id}/statement ───────────────────────────────────────────────

@patch("functions.payments.payments.PaymentUoW")
def test_get_statement_200_no_payments(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow()
    result = payments.handler(_event("GET /v1/members/{id}/statement", None,
                                     {"id": "member-uuid-1234"}), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["invoice"]["outstanding"] == 60.0
    assert body["payments"] == []


@patch("functions.payments.payments.PaymentUoW")
def test_get_statement_200_own_statement(mock_uow_cls):
    mock_uow_cls.return_value = _make_uow(caller=REGULAR_MEMBER,
                                           member_by_id={"id": "member-uuid-1234", "membership_id": "m-uuid"})
    result = payments.handler(_event("GET /v1/members/{id}/statement", None,
                                     {"id": "member-uuid-1234"}), generate_context())
    assert result["statusCode"] == 200


@patch("functions.payments.payments.PaymentUoW")
def test_get_statement_403_other_member(mock_uow_cls):
    uow = _make_uow(caller=REGULAR_MEMBER)
    uow.members.get_by_id.return_value = {"id": "other-member-uuid", "membership_id": "m-uuid"}
    mock_uow_cls.return_value = uow
    result = payments.handler(_event("GET /v1/members/{id}/statement", None,
                                     {"id": "other-member-uuid"}), generate_context())
    assert result["statusCode"] == 403


@patch("functions.payments.payments.PaymentUoW")
def test_get_statement_404_member_not_found(mock_uow_cls):
    uow = _make_uow()
    uow.members.get_by_id.return_value = None
    mock_uow_cls.return_value = uow
    result = payments.handler(_event("GET /v1/members/{id}/statement", None,
                                     {"id": "nonexistent"}), generate_context())
    assert result["statusCode"] == 404


@patch("functions.payments.payments.PaymentUoW")
def test_get_statement_200_no_active_period(mock_uow_cls):
    uow = _make_uow()
    uow.periods.get_active_for_membership.return_value = None
    mock_uow_cls.return_value = uow
    result = payments.handler(_event("GET /v1/members/{id}/statement", None,
                                     {"id": "member-uuid-1234"}), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["period"] is None
    assert body["invoice"] is None


@patch("functions.payments.payments.PaymentUoW")
def test_get_statement_200_no_invoice(mock_uow_cls):
    uow = _make_uow(invoice_by_period=None)
    uow.invoices.get_by_period_id.return_value = None
    mock_uow_cls.return_value = uow
    result = payments.handler(_event("GET /v1/members/{id}/statement", None,
                                     {"id": "member-uuid-1234"}), generate_context())
    assert result["statusCode"] == 200
    body = json.loads(result["body"])
    assert body["period"] is not None
    assert body["invoice"] is None
