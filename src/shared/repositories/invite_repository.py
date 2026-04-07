from datetime import datetime, timedelta, timezone

from shared.instrumentation.tracer import tracer
from shared.models.invite_request import InviteRequest
from shared.reference_data.invite_status import InviteStatus

INVITE_EXPIRY_DAYS = 30


class InviteRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="InvitePendingExists")
    def pending_exists(self, mobile: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM invites WHERE mobile = %s AND status = %s)",
                (mobile, InviteStatus.PENDING.value),
            )
            return cur.fetchone()[0]

    @tracer.capture_method(name="InviteInsert")
    def insert(self, invite_request: InviteRequest, activation_code: str, invited_by: str):
        expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO invites (
                    first_name, last_name, mobile, activation_code,
                    invited_by, relationship, status, is_legacy, expires_at, date_joined
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    invite_request.first_name,
                    invite_request.last_name,
                    invite_request.mobile,
                    activation_code,
                    invited_by,
                    invite_request.relationship,
                    InviteStatus.PENDING.value,
                    invite_request.is_legacy,
                    expires_at,
                    invite_request.date_joined,
                ),
            )

    @tracer.capture_method(name="InviteGetByActivationCode")
    def get_by_activation_code(self, activation_code: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, status, relationship, mobile, first_name, last_name,
                       invited_by, is_legacy, expires_at, date_joined
                FROM invites
                WHERE activation_code = %s
                """,
                (activation_code,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="InviteMarkUsed")
    def mark_used(self, invite_id: str, member_id: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE invites SET status = %s, member_id = %s WHERE id = %s",
                (InviteStatus.USED.value, member_id, invite_id),
            )

    @tracer.capture_method(name="InviteMarkExpired")
    def mark_expired(self, invite_id: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE invites SET status = %s WHERE id = %s",
                (InviteStatus.EXPIRED.value, invite_id),
            )
