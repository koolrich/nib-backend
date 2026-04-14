from shared.instrumentation.tracer import tracer


class EventRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="EventInsert")
    def insert(self, title: str, date: str, type: str, description: str | None, created_by: str) -> dict:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO events (title, date, type, status, description, created_by)
                VALUES (%s, %s, %s, 'upcoming', %s, %s)
                RETURNING id, title, date, type, status, description, created_by, created_at
                """,
                (title, date, type, description, created_by),
            )
            return cur.fetchone()

    @tracer.capture_method(name="EventGetAll")
    def get_all(self) -> list:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.id, e.title, e.date, e.type, e.status, e.description,
                    e.created_by, e.created_at,
                    COALESCE(SUM(ec.amount), 0) AS total_contributions,
                    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'pledged') AS total_pledges
                FROM events e
                LEFT JOIN event_contributions ec ON ec.event_id = e.id
                LEFT JOIN pledges p ON p.event_id = e.id
                GROUP BY e.id
                ORDER BY e.date DESC
                """,
            )
            return cur.fetchall()

    @tracer.capture_method(name="EventGetById")
    def get_by_id(self, event_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    e.id, e.title, e.date, e.type, e.status, e.description,
                    e.created_by, e.created_at,
                    COALESCE(SUM(ec.amount), 0) AS total_contributions,
                    COUNT(DISTINCT p.id) FILTER (WHERE p.status = 'pledged') AS total_pledges
                FROM events e
                LEFT JOIN event_contributions ec ON ec.event_id = e.id
                LEFT JOIN pledges p ON p.event_id = e.id
                WHERE e.id = %s
                GROUP BY e.id
                """,
                (event_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="EventUpdate")
    def update(self, event_id: str, fields: dict) -> dict | None:
        allowed = {"title", "date", "type", "status", "description"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_by_id(event_id)

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [event_id]

        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE events
                SET {set_clause}, updated_at = NOW()
                WHERE id = %s
                RETURNING id, title, date, type, status, description, updated_at
                """,
                values,
            )
            return cur.fetchone()

    @tracer.capture_method(name="EventHasItemsOrPledges")
    def has_items_or_pledges(self, event_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT 1 FROM event_items WHERE event_id = %s
                    UNION ALL
                    SELECT 1 FROM pledges WHERE event_id = %s
                )
                """,
                (event_id, event_id),
            )
            row = cur.fetchone()
            return row["exists"] if row else False

    @tracer.capture_method(name="EventGetItems")
    def get_items(self, event_id: str) -> list:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ei.id, ei.event_id, ei.name, ei.unit, ei.quantity_needed,
                    COALESCE(SUM(p.quantity) FILTER (WHERE p.status = 'pledged'), 0) AS quantity_pledged,
                    ei.quantity_needed - COALESCE(SUM(p.quantity) FILTER (WHERE p.status = 'pledged'), 0) AS quantity_remaining
                FROM event_items ei
                LEFT JOIN pledges p ON p.event_item_id = ei.id
                WHERE ei.event_id = %s
                GROUP BY ei.id
                ORDER BY ei.created_at
                """,
                (event_id,),
            )
            rows = cur.fetchall()
            result = []
            for row in rows:
                r = dict(row)
                r["is_available"] = r["quantity_remaining"] > 0
                result.append(r)
            return result

    @tracer.capture_method(name="EventGetItemById")
    def get_item_by_id(self, item_id: str, event_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, event_id, name, quantity_needed, unit, created_at FROM event_items WHERE id = %s AND event_id = %s",
                (item_id, event_id),
            )
            return cur.fetchone()

    @tracer.capture_method(name="EventItemHasActivePledges")
    def item_has_active_pledges(self, item_id: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM pledges WHERE event_item_id = %s AND status = 'pledged')",
                (item_id,),
            )
            return cur.fetchone()["exists"]

    @tracer.capture_method(name="EventUpdateItem")
    def update_item(self, item_id: str, fields: dict) -> dict:
        allowed = {"name", "quantity_needed", "unit"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_item_by_id(item_id, None)

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [item_id]
        with self.conn.cursor() as cur:
            cur.execute(
                f"UPDATE event_items SET {set_clause} WHERE id = %s RETURNING id, event_id, name, quantity_needed, unit, created_at",
                values,
            )
            return cur.fetchone()

    @tracer.capture_method(name="EventDeleteItem")
    def delete_item(self, item_id: str):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM event_items WHERE id = %s", (item_id,))

    @tracer.capture_method(name="EventInsertItems")
    def insert_items(self, event_id: str, items: list) -> list:
        results = []
        with self.conn.cursor() as cur:
            for item in items:
                cur.execute(
                    """
                    INSERT INTO event_items (event_id, name, quantity_needed, unit)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, event_id, name, quantity_needed, unit, created_at
                    """,
                    (event_id, item["name"], item["quantity_needed"], item["unit"]),
                )
                results.append(cur.fetchone())
        return results

    @tracer.capture_method(name="EventGetPledges")
    def get_pledges(self, event_id: str) -> list:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    p.id, p.event_id, p.member_id,
                    m.first_name || ' ' || m.last_name AS member_name,
                    p.event_item_id, ei.name AS item_name,
                    p.quantity, p.status, p.created_at
                FROM pledges p
                JOIN members m ON m.id = p.member_id
                JOIN event_items ei ON ei.id = p.event_item_id
                WHERE p.event_id = %s
                  AND p.status = 'pledged'
                ORDER BY p.created_at
                """,
                (event_id,),
            )
            return cur.fetchall()

    @tracer.capture_method(name="EventGetContributions")
    def get_contributions(self, event_id: str) -> list:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    ec.id, ec.event_id, ec.member_id,
                    COALESCE(m.first_name || ' ' || m.last_name, 'Anonymous') AS member_name,
                    ec.pledge_id, ec.amount, ec.received_at, ec.note
                FROM event_contributions ec
                LEFT JOIN members m ON m.id = ec.member_id
                WHERE ec.event_id = %s
                ORDER BY ec.received_at
                """,
                (event_id,),
            )
            return cur.fetchall()

    @tracer.capture_method(name="EventInsertContribution")
    def insert_contribution(self, event_id: str, member_id: str | None, pledge_id: str | None,
                            amount: float, recorded_by: str, received_at: str, note: str | None) -> dict:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO event_contributions
                    (event_id, member_id, pledge_id, amount, recorded_by, received_at, note)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id, event_id, member_id, pledge_id, amount, recorded_by, received_at, note, created_at
                """,
                (event_id, member_id, pledge_id, amount, recorded_by, received_at, note),
            )
            return cur.fetchone()

    @tracer.capture_method(name="EventGetContributionById")
    def get_contribution_by_id(self, contribution_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM event_contributions WHERE id = %s",
                (contribution_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="EventDeleteContribution")
    def delete_contribution(self, contribution_id: str):
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM event_contributions WHERE id = %s", (contribution_id,))
