from shared.instrumentation.tracer import tracer


class PledgeRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="PledgeGetByMember")
    def get_by_member(self, member_id: str) -> list:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p.id, p.event_id, e.title AS event_title, e.date AS event_date,
                    ei.name AS item_name, ei.unit,
                    p.quantity, p.status, p.created_at,
                    ec.amount AS contribution_amount,
                    ec.received_at AS contribution_received_at
                FROM pledges p
                JOIN events e ON e.id = p.event_id
                JOIN event_items ei ON ei.id = p.event_item_id
                LEFT JOIN event_contributions ec ON ec.pledge_id = p.id
                WHERE p.member_id = %s
                  AND p.status = 'pledged'
                  AND e.status = 'upcoming'
                ORDER BY e.date, p.created_at
                """,
                (member_id,),
            )
            return cur.fetchall()

    @tracer.capture_method(name="PledgeGetItemById")
    def get_item_by_id(self, event_item_id: str, event_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, event_id, name, quantity_needed FROM event_items WHERE id = %s AND event_id = %s",
                (event_item_id, event_id),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PledgeGetExisting")
    def get_existing(self, member_id: str, event_item_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, quantity, status FROM pledges WHERE member_id = %s AND event_item_id = %s",
                (member_id, event_item_id),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PledgeGetQuantityRemaining")
    def get_quantity_remaining(self, event_item_id: str, exclude_member_id: str | None = None) -> float:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ei.quantity_needed - COALESCE(
                        SUM(p.quantity) FILTER (
                            WHERE p.status = 'pledged'
                            AND (%s::uuid IS NULL OR p.member_id != %s::uuid)
                        ), 0
                    ) AS quantity_remaining
                FROM event_items ei
                LEFT JOIN pledges p ON p.event_item_id = ei.id
                WHERE ei.id = %s
                GROUP BY ei.quantity_needed
                """,
                (exclude_member_id, exclude_member_id, event_item_id),
            )
            row = cur.fetchone()
            return float(row["quantity_remaining"]) if row else 0.0

    @tracer.capture_method(name="PledgeInsert")
    def insert(self, event_id: str, member_id: str, event_item_id: str, quantity: float) -> dict:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pledges (event_id, member_id, event_item_id, quantity, status)
                VALUES (%s, %s, %s, %s, 'pledged')
                RETURNING id, event_id, member_id, event_item_id, quantity, status, created_at
                """,
                (event_id, member_id, event_item_id, quantity),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PledgeGetById")
    def get_by_id(self, pledge_id: str, event_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.event_id, p.member_id, p.event_item_id,
                       ei.name AS item_name, p.quantity, p.status, p.updated_at
                FROM pledges p
                JOIN event_items ei ON ei.id = p.event_item_id
                WHERE p.id = %s AND p.event_id = %s
                """,
                (pledge_id, event_id),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PledgeGetByIdForContribution")
    def get_by_id_for_contribution(self, pledge_id: str, event_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, event_id, status FROM pledges WHERE id = %s AND event_id = %s",
                (pledge_id, event_id),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PledgeUpdateQuantity")
    def update_quantity(self, pledge_id: str, quantity: float) -> dict:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pledges SET quantity = %s, updated_at = NOW()
                WHERE id = %s
                RETURNING id, event_id, member_id, event_item_id, quantity, status, updated_at
                """,
                (quantity, pledge_id),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PledgeCancel")
    def cancel(self, pledge_id: str) -> dict:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                UPDATE pledges SET status = 'cancelled', updated_at = NOW()
                WHERE id = %s
                RETURNING id, status, updated_at
                """,
                (pledge_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="PledgeHasContribution")
    def has_contribution(self, pledge_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM event_contributions WHERE pledge_id = %s)",
                (pledge_id,),
            )
            row = cur.fetchone()
            return row["exists"] if row else False
