from aws_lambda_powertools import Logger
from shared.instrumentation.tracer import tracer

logger = Logger()


@tracer.capture_method(name="GetEventItemById")
def get_event_item_by_id(conn, event_item_id: str, event_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, event_id, name, quantity_needed FROM event_items WHERE id = %s AND event_id = %s",
            (event_item_id, event_id),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetExistingPledge")
def get_existing_pledge(conn, member_id: str, event_item_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, quantity, status FROM pledges WHERE member_id = %s AND event_item_id = %s",
            (member_id, event_item_id),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetQuantityRemaining")
def get_quantity_remaining(conn, event_item_id: str, exclude_member_id: str | None = None) -> float:
    """Returns quantity remaining for an item, optionally excluding a member's existing pledge."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                ei.quantity_needed - COALESCE(
                    SUM(p.quantity) FILTER (
                        WHERE p.status = 'pledged'
                        AND (%s IS NULL OR p.member_id != %s::uuid)
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


@tracer.capture_method(name="InsertPledge")
def insert_pledge(conn, event_id: str, member_id: str, event_item_id: str, quantity: float) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO pledges (event_id, member_id, event_item_id, quantity, status)
            VALUES (%s, %s, %s, %s, 'pledged')
            RETURNING id, event_id, member_id, event_item_id, quantity, status, created_at
            """,
            (event_id, member_id, event_item_id, quantity),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetPledgeById")
def get_pledge_by_id(conn, pledge_id: str, event_id: str) -> dict | None:
    with conn.cursor() as cur:
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


@tracer.capture_method(name="UpdatePledgeQuantity")
def update_pledge_quantity(conn, pledge_id: str, quantity: float) -> dict:
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE pledges SET quantity = %s, updated_at = NOW()
            WHERE id = %s
            RETURNING id, event_id, member_id, event_item_id, quantity, status, updated_at
            """,
            (quantity, pledge_id),
        )
        return cur.fetchone()


@tracer.capture_method(name="CancelPledge")
def cancel_pledge(conn, pledge_id: str) -> dict:
    with conn.cursor() as cur:
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
def pledge_has_contribution(conn, pledge_id: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM event_contributions WHERE pledge_id = %s)",
            (pledge_id,),
        )
        row = cur.fetchone()
        return row[0] if row else False


@tracer.capture_method(name="GetPledgeById")
def get_pledge_by_id_for_contribution(conn, pledge_id: str, event_id: str) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, event_id, status FROM pledges WHERE id = %s AND event_id = %s",
            (pledge_id, event_id),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetMemberPledges")
def get_member_pledges(conn, member_id: str) -> list:
    with conn.cursor() as cur:
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
