from datetime import date, timedelta

from shared.instrumentation.tracer import tracer
from shared.reference_data.invoice_status import InvoiceStatus


class InvoiceRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="InvoiceGetCurrentFee")
    def get_current_fee(self, membership_type: str) -> dict:
        with self.conn.cursor() as cur:
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

    @tracer.capture_method(name="InvoiceGenerateNumber")
    def generate_number(self) -> str:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT 'NIB-' || LPAD(nextval('invoice_number_seq')::TEXT, 4, '0') AS invoice_number"
            )
            return cur.fetchone()["invoice_number"]

    @tracer.capture_method(name="InvoiceInsert")
    def insert(self, membership_period_id: str, membership_type: str) -> dict:
        fee = self.get_current_fee(membership_type)
        invoice_number = self.generate_number()
        today = date.today()
        due_date = today + timedelta(days=fee["due_days"])
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO invoices (
                    membership_period_id, invoice_number, issue_date, due_date,
                    amount_due, status
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id, membership_period_id, invoice_number, issue_date,
                          due_date, amount_due, status, created_at
                """,
                (membership_period_id, invoice_number, today, due_date,
                 fee["annual_fee"], InvoiceStatus.UNPAID.value),
            )
            return cur.fetchone()

    @tracer.capture_method(name="InvoiceGetById")
    def get_by_id(self, invoice_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, membership_period_id, invoice_number, issue_date, due_date,
                       amount_due, status, created_at
                FROM invoices WHERE id = %s
                """,
                (invoice_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="InvoiceGetByPeriodId")
    def get_by_period_id(self, period_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, membership_period_id, invoice_number, issue_date, due_date,
                       amount_due, status, created_at
                FROM invoices WHERE membership_period_id = %s
                """,
                (period_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="InvoiceUpdateStatus")
    def update_status(self, invoice_id: str, status: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE invoices SET status = %s WHERE id = %s",
                (status, invoice_id),
            )
