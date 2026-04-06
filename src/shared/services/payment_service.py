from decimal import Decimal

from shared.instrumentation.tracer import tracer
from shared.reference_data.invoice_status import InvoiceStatus
from aws_lambda_powertools import Logger

logger = Logger()

VALID_PAYMENT_METHODS = {"bank_transfer", "cash", "cheque", "other"}


@tracer.capture_method(name="GetMemberWithMembershipType")
def get_member_with_membership_type(conn, member_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT m.id, m.is_legacy, m.membership_id, ms.membership_type
            FROM members m
            LEFT JOIN memberships ms ON ms.id = m.membership_id
            WHERE m.id = %s
            """,
            (member_id,),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetActivePeriodForMembership")
def get_active_period_for_membership(conn, membership_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, membership_id, start_date, end_date, status, created_at
            FROM membership_periods
            WHERE membership_id = %s AND status = 'active'
            ORDER BY start_date DESC
            LIMIT 1
            """,
            (membership_id,),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetInvoiceByPeriodId")
def get_invoice_by_period_id(conn, period_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, membership_period_id, invoice_number, issue_date, due_date,
                   amount_due, status, created_at
            FROM invoices WHERE membership_period_id = %s
            """,
            (period_id,),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetInvoiceById")
def get_invoice_by_id(conn, invoice_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, membership_period_id, invoice_number, issue_date, due_date,
                   amount_due, status, created_at
            FROM invoices WHERE id = %s
            """,
            (invoice_id,),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetTotalPaid")
def get_total_paid(conn, invoice_id: str) -> Decimal:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE invoice_id = %s",
            (invoice_id,),
        )
        return cur.fetchone()["total"]


@tracer.capture_method(name="GetPaymentsByInvoice")
def get_payments_by_invoice(conn, invoice_id: str) -> list:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, amount, method, reference, received_by, received_at, note, created_at
            FROM payments WHERE invoice_id = %s
            ORDER BY received_at ASC
            """,
            (invoice_id,),
        )
        return cur.fetchall()


@tracer.capture_method(name="InsertPayment")
def insert_payment(conn, invoice_id: str, amount, method: str, reference,
                   received_by: str, received_at: str, note) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO payments (invoice_id, amount, method, reference, received_by, received_at, note)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, invoice_id, amount, method, reference, received_by,
                      received_at, note, created_at
            """,
            (invoice_id, amount, method, reference, received_by, received_at, note),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetPaymentById")
def get_payment_by_id(conn, payment_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, invoice_id, amount, method, reference, received_by, received_at, note, created_at
            FROM payments WHERE id = %s
            """,
            (payment_id,),
        )
        return cur.fetchone()


@tracer.capture_method(name="DeletePayment")
def delete_payment(conn, payment_id: str):
    with conn.cursor() as cur:
        cur.execute("DELETE FROM payments WHERE id = %s", (payment_id,))


@tracer.capture_method(name="UpdateInvoiceStatus")
def update_invoice_status(conn, invoice_id: str, status: str):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE invoices SET status = %s WHERE id = %s",
            (status, invoice_id),
        )
