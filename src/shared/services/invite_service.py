import uuid
import boto3
from datetime import datetime, timedelta, timezone

from shared.db import get_connection
from shared.models.invite_request import InviteRequest
from shared.instrumentation.tracer import tracer
from shared.reference_data.invite_status import InviteStatus
from aws_lambda_powertools import Logger

logger = Logger()

INVITE_EXPIRY_DAYS = 30


@tracer.capture_method(name="CheckMobileAlreadyMember")
def mobile_is_member(conn, mobile: str) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT EXISTS (SELECT 1 FROM members WHERE mobile = %s)", (mobile,))
        return cur.fetchone()[0]


@tracer.capture_method(name="CheckPendingInviteExists")
def pending_invite_exists(conn, mobile: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT EXISTS (SELECT 1 FROM invites WHERE mobile = %s AND status = %s)",
            (mobile, InviteStatus.PENDING.value),
        )
        return cur.fetchone()[0]


@tracer.capture_method(name="InsertInvite")
def insert_invite(conn, invite_request: InviteRequest, activation_code: str, invited_by: str):
    expires_at = datetime.now(timezone.utc) + timedelta(days=INVITE_EXPIRY_DAYS)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO invites (
                first_name, last_name, mobile, activation_code,
                invited_by, relationship, status, expires_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                invite_request.first_name,
                invite_request.last_name,
                invite_request.mobile,
                activation_code,
                invited_by,
                invite_request.relationship,
                InviteStatus.PENDING.value,
                expires_at,
            ),
        )


@tracer.capture_method(name="GetInviteByActivationCode")
def get_invite_by_activation_code(conn, activation_code: str):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, status, relationship, mobile, first_name, last_name,
                   invited_by, is_legacy, expires_at
            FROM invites
            WHERE activation_code = %s
            """,
            (activation_code,),
        )
        return cur.fetchone()


@tracer.capture_method(name="MarkInviteUsed")
def mark_invite_used(conn, invite_id: str, member_id: str):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE invites SET status = %s, member_id = %s WHERE id = %s",
            (InviteStatus.USED.value, member_id, invite_id),
        )


@tracer.capture_method(name="MarkInviteExpired")
def mark_invite_expired(conn, invite_id: str):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE invites SET status = %s WHERE id = %s",
            (InviteStatus.EXPIRED.value, invite_id),
        )


@tracer.capture_method(name="SendInviteSMS")
def publish_invite_sms(mobile: str, activation_code: str):
    sns = boto3.client("sns")
    response = sns.publish(
        PhoneNumber=mobile,
        Message=f"Your activation code is: {activation_code}",
        MessageAttributes={
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": "Transactional",
            }
        },
    )

    status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    if status_code != 200:
        logger.error(
            "SMS may not have been sent successfully", extra={"sns_response": response}
        )
        raise RuntimeError(f"SNS publish failed with status {status_code}")


def generate_activation_code() -> str:
    return uuid.uuid4().hex[:8].upper()
