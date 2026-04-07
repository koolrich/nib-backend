from datetime import date

from shared.instrumentation.tracer import tracer
from shared.models.register_request import RegisterRequest


class MemberRepository:
    def __init__(self, conn):
        self.conn = conn

    @tracer.capture_method(name="MemberGetByCognitoSub")
    def get_by_cognito_sub(self, cognito_sub: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT id, member_role FROM members WHERE cognito_user_id = %s",
                (cognito_sub,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="MemberMobileExists")
    def mobile_exists(self, mobile: str) -> bool:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS (SELECT 1 FROM members WHERE mobile = %s)",
                (mobile,),
            )
            return cur.fetchone()[0]

    @tracer.capture_method(name="MemberInsert")
    def insert(self, request: RegisterRequest, cognito_sub: str, invited_by: str,
               is_legacy: bool, date_joined=None) -> str:
        with self.conn.cursor() as cur:
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
                    date_joined if date_joined else date.today(),
                ),
            )
            return str(cur.fetchone()["id"])

    @tracer.capture_method(name="MemberGetById")
    def get_by_id(self, member_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, first_name, last_name, email, mobile, address_line1, address_line2,
                       town, post_code, state_of_origin, lga, birthday_day, birthday_month,
                       relationship_status, emergency_contact_name, emergency_contact_phone,
                       member_role, status, is_legacy, date_joined, membership_id
                FROM members WHERE id = %s
                """,
                (member_id,),
            )
            return cur.fetchone()

    @tracer.capture_method(name="MemberUpdate")
    def update(self, member_id: str, fields: dict) -> dict | None:
        profile_fields = {
            "first_name", "last_name", "email", "mobile", "address_line1", "address_line2",
            "town", "post_code", "state_of_origin", "lga", "birthday_day", "birthday_month",
            "relationship_status", "emergency_contact_name", "emergency_contact_phone",
        }
        restricted_fields = {"member_role", "status"}
        allowed = profile_fields | restricted_fields

        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return self.get_by_id(member_id)

        set_clause = ", ".join(f"{k} = %s" for k in updates)
        values = list(updates.values()) + [member_id]

        with self.conn.cursor() as cur:
            cur.execute(
                f"""
                UPDATE members
                SET {set_clause}, updated_at = NOW()
                WHERE id = %s
                RETURNING id, first_name, last_name, email, mobile, address_line1, address_line2,
                          town, post_code, state_of_origin, lga, birthday_day, birthday_month,
                          relationship_status, emergency_contact_name, emergency_contact_phone,
                          member_role, status, updated_at
                """,
                values,
            )
            return cur.fetchone()

    @tracer.capture_method(name="MemberGetWithMembershipType")
    def get_with_membership_type(self, member_id: str) -> dict | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.id, m.is_legacy, m.membership_id, ms.membership_type
                FROM members m
                LEFT JOIN memberships ms ON ms.id = m.membership_id
                WHERE m.id = %s
                """,
                (member_id,),
            )
            return cur.fetchone()
