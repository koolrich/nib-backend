from shared.instrumentation.tracer import tracer


class MembershipRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="MembershipInsert")
    def insert(self, membership_type: str, primary_member_id: str) -> str:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memberships (membership_type, primary_member_id)
                VALUES (%s, %s)
                RETURNING id
                """,
                (membership_type, primary_member_id),
            )
            return str(cur.fetchone()["id"])

    @tracer.capture_method(name="MembershipGetIdByMemberId")
    def get_id_by_member_id(self, member_id: str) -> str | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT membership_id FROM members WHERE id = %s",
                (member_id,),
            )
            row = cur.fetchone()
            return str(row["membership_id"]) if row else None

    @tracer.capture_method(name="MembershipUpdateMemberId")
    def update_member_membership_id(self, member_id: str, membership_id: str):
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE members SET membership_id = %s WHERE id = %s",
                (membership_id, member_id),
            )
