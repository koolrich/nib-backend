from datetime import date
from dateutil.relativedelta import relativedelta

from shared.instrumentation.tracer import tracer
from shared.reference_data.membership_period_status import MembershipPeriodStatus


class MembershipPeriodRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="MembershipPeriodInsert")
    def insert(self, membership_id: str, start_date=None, end_date=None) -> dict:
        today = date.today()
        start = start_date or today
        end = end_date or (today + relativedelta(years=1))
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO membership_periods (membership_id, start_date, end_date, status)
                VALUES (%s, %s, %s, %s)
                RETURNING id, membership_id, start_date, end_date, status, created_at
                """,
                (membership_id, start, end, MembershipPeriodStatus.ACTIVE.value),
            )
            return cur.fetchone()

    @tracer.capture_method(name="MembershipPeriodGetById")
    def get_by_id(self, period_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, membership_id, start_date, end_date, status, created_at
                FROM membership_periods WHERE id = %s
                """,
                (period_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="MembershipPeriodUpdate")
    def update(self, period_id: str, fields: dict) -> dict | None:
        allowed = {"start_date", "end_date", "status"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_by_id(period_id)

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [period_id]

        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE membership_periods
                SET {set_clause}, updated_at = NOW()
                WHERE id = %s
                RETURNING id, membership_id, start_date, end_date, status, created_at
                """,
                values,
            )
            return cur.fetchone()

    @tracer.capture_method(name="MembershipPeriodGetActive")
    def get_active_for_membership(self, membership_id: str) -> dict | None:
        with self.conn.cursor() as cur:
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
