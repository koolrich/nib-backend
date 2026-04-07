from decimal import Decimal

from shared.instrumentation.tracer import tracer

VALID_PAYMENT_METHODS = {"bank_transfer", "cash", "cheque", "other"}


class PaymentRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="PaymentGetById")
    def get_by_id(self, payment_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, invoice_id, amount, method, reference, received_by,
                       received_at, note, created_at
                FROM payments WHERE id = %s
                """,
                (payment_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PaymentInsert")
    def insert(self, invoice_id: str, amount, method: str, reference,
               received_by: str, received_at: str, note) -> dict:
        with self.conn.cursor() as cur:
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

    @tracer.capture_method(name="PaymentDelete")
    def delete(self, payment_id: str):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM payments WHERE id = %s", (payment_id,))

    @tracer.capture_method(name="PaymentGetTotalByInvoice")
    def get_total_by_invoice(self, invoice_id: str) -> Decimal:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE invoice_id = %s",
                (invoice_id,),
            )
            return cur.fetchone()["total"]

    @tracer.capture_method(name="PaymentGetAllByInvoice")
    def get_all_by_invoice(self, invoice_id: str) -> list:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, amount, method, reference, received_by, received_at, note, created_at
                FROM payments WHERE invoice_id = %s
                ORDER BY received_at ASC
                """,
                (invoice_id,),
            )
            return cur.fetchall()
