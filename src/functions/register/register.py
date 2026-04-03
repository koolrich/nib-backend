import json
from typing import Dict, Any

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayEnvelope
from aws_lambda_powertools.utilities.typing import LambdaContext
from pydantic import ValidationError

from shared.db import get_connection
from shared.instrumentation.tracer import tracer
from shared.models.register_request import RegisterRequest
from shared.services.cognito_service import sign_up, confirm_sign_up, delete_user
from shared.services.invite_service import get_invite_by_activation_code, mark_invite_used
from shared.services.member_service import insert_member, get_member_membership_id, update_member_membership_id
from shared.services.membership_service import (
    get_current_fee,
    insert_membership,
    insert_membership_period,
    generate_invoice_number,
    insert_invoice,
)

logger = Logger()


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event: Dict[str, Any], context: LambdaContext):
    return register(event)


@tracer.capture_method
def register(event: Dict[str, Any]):
    conn = None
    cognito_created = False
    cognito_sub = None

    try:
        request = parse(event=event, model=RegisterRequest, envelope=ApiGatewayEnvelope)

        conn = get_connection()

        invite = get_invite_by_activation_code(conn, request.activation_code)
        if not invite:
            return {"statusCode": 404, "body": json.dumps({"error": "Invalid activation code"})}

        if invite["relationship"] == "other" and not request.membership_type:
            return {"statusCode": 400, "body": json.dumps({"error": "membership_type is required"})}

        # Cognito sign up — done before DB writes so we have cognito_sub
        cognito_sub = sign_up(request.mobile, request.password)
        cognito_created = True
        confirm_sign_up(cognito_sub)

        # Create member record
        member_id = insert_member(conn, request, cognito_sub, invite["invited_by"], invite["is_legacy"])

        # Membership setup
        if invite["relationship"] == "other":
            fee = get_current_fee(conn, request.membership_type)
            membership_id = insert_membership(conn, request.membership_type, member_id)
            update_member_membership_id(conn, member_id, membership_id)
            period_id = insert_membership_period(conn, membership_id)
            invoice_number = generate_invoice_number(conn)
            insert_invoice(conn, period_id, invoice_number, fee)
        else:
            # Spouse — link to inviter's existing membership
            inviter_membership_id = get_member_membership_id(conn, str(invite["invited_by"]))
            if not inviter_membership_id:
                raise RuntimeError("Inviter has no membership to link spouse to")
            update_member_membership_id(conn, member_id, inviter_membership_id)

        mark_invite_used(conn, str(invite["id"]), member_id)
        conn.commit()

        return {"statusCode": 201, "body": json.dumps({"message": "Registration successful"})}

    except ValidationError as ve:
        logger.warning("Validation error", extra={"error": str(ve)})
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    except Exception as e:
        if cognito_created and cognito_sub:
            try:
                delete_user(cognito_sub)
                logger.info("Rolled back Cognito user", extra={"cognito_sub": cognito_sub})
            except Exception as ce:
                logger.exception("Failed to rollback Cognito user", extra={"error": str(ce)})
        if conn:
            conn.rollback()
        logger.exception("Unexpected error during registration", extra={"error": str(e)})
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    finally:
        if conn:
            conn.close()
