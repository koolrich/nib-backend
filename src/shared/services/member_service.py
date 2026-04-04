from datetime import date

from shared.instrumentation.tracer import tracer
from shared.models.register_request import RegisterRequest
from aws_lambda_powertools import Logger

logger = Logger()


@tracer.capture_method(name="GetMemberByCognitoSub")
def get_member_by_cognito_sub(conn, cognito_sub: str):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM members WHERE cognito_user_id = %s",
            (cognito_sub,),
        )
        return cur.fetchone()


@tracer.capture_method(name="GetMemberContext")
def get_member_context(conn, cognito_sub: str) -> dict | None:
    """Returns {id, role} for the calling member, or None if not found."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, member_role FROM members WHERE cognito_user_id = %s",
            (cognito_sub,),
        )
        return cur.fetchone()


@tracer.capture_method(name="InsertMember")
def insert_member(conn, request: RegisterRequest, cognito_sub: str, invited_by: str, is_legacy: bool) -> str:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO members (
                cognito_user_id, mobile, email, first_name, last_name,
                address_line1, address_line2, town, post_code,
                state_of_origin, lga, birthday_day, birthday_month,
                relationship_status, emergency_contact_name, emergency_contact_phone,
                member_role, status, is_legacy, date_joined
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                cognito_sub,
                request.mobile,
                request.email,
                request.first_name,
                request.last_name,
                request.address_line1,
                request.address_line2,
                request.town,
                request.post_code,
                request.state_of_origin,
                request.lga,
                request.birthday_day,
                request.birthday_month,
                request.relationship_status,
                request.emergency_contact_name,
                request.emergency_contact_phone,
                "member",
                "active",
                is_legacy,
                date.today(),
            ),
        )
        row = cur.fetchone()
        return str(row["id"])


@tracer.capture_method(name="GetMemberMembershipId")
def get_member_membership_id(conn, member_id: str) -> str:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT membership_id FROM members WHERE id = %s",
            (member_id,),
        )
        row = cur.fetchone()
        return str(row["membership_id"]) if row else None


@tracer.capture_method(name="UpdateMemberMembershipId")
def update_member_membership_id(conn, member_id: str, membership_id: str):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE members SET membership_id = %s WHERE id = %s",
            (membership_id, member_id),
        )
