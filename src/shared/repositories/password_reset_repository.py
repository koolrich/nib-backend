from datetime import datetime, timezone

from shared.instrumentation.tracer import tracer


class PasswordResetRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="PasswordResetInsert")
    def insert(self, member_id: str, code_hash: str, expires_at: datetime):
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO password_reset_tokens (member_id, code_hash, expires_at)
                VALUES (%s, %s, %s)
                """,
                (member_id, code_hash, expires_at),
            )

    @tracer.capture_method(name="PasswordResetGetValid")
    def get_valid(self, member_id: str) -> dict | None:
        """Returns the most recent unused, unexpired token for this member."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, code_hash
                FROM password_reset_tokens
                WHERE member_id = %s
                  AND used_at IS NULL
                  AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (member_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PasswordResetMarkUsed")
    def mark_used(self, token_id: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE password_reset_tokens SET used_at = NOW() WHERE id = %s",
                (token_id,),
            )
