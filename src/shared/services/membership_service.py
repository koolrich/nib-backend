from datetime import date
from dateutil.relativedelta import relativedelta

from shared.instrumentation.tracer import tracer
from shared.reference_data.invoice_status import InvoiceStatus
from shared.reference_data.membership_period_status import MembershipPeriodStatus
from aws_lambda_powertools import Logger

logger = Logger()


@tracer.capture_method(name="GetCurrentFee")
def get_current_fee(conn, membership_type: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT annual_fee, due_days FROM membership_fees
            WHERE membership_type = %s AND effective_from <= %s
            ORDER BY effective_from DESC
            LIMIT 1
            """,
            (membership_type, date.today()),
        )
        row = cur.fetchone()
        if not row:
            raise RuntimeError(f"No fee configured for membership type: {membership_type}")
        return row


@tracer.capture_method(name="InsertMembership")
def insert_membership(conn, membership_type: str, primary_member_id: str) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO memberships (membership_type, primary_member_id)
            VALUES (%s, %s)
            RETURNING id
            """,
            (membership_type, primary_member_id),
        )
        row = cur.fetchone()
        return str(row["id"])


@tracer.capture_method(name="InsertMembershipPeriod")
def insert_membership_period(conn, membership_id: str) -> str:
    today = date.today()
    period_end = today + relativedelta(years=1)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO membership_periods (membership_id, start_date, end_date, status)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (membership_id, today, period_end, MembershipPeriodStatus.ACTIVE.value),
        )
        row = cur.fetchone()
        return str(row["id"])


@tracer.capture_method(name="GenerateInvoiceNumber")
def generate_invoice_number(conn) -> str:
    with conn.cursor() as cur:
        cur.execute("SELECT 'NIB-' || LPAD(nextval('invoice_number_seq')::TEXT, 4, '0') AS invoice_number")
        row = cur.fetchone()
        return row["invoice_number"]


@tracer.capture_method(name="InsertInvoice")
def insert_invoice(conn, membership_period_id: str, invoice_number: str, amount_due, due_date):
    today = date.today()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO invoices (
                membership_period_id, invoice_number, issue_date, due_date,
                amount_due, status
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (membership_period_id, invoice_number, today, due_date, amount_due, InvoiceStatus.UNPAID.value),
        )
