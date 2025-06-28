import json
import uuid
import boto3
from shared.db import get_connection
from pydantic import ValidationError
from typing import Dict, Any
from aws_lambda_powertools.utilities.typing import LambdaContext
from aws_lambda_powertools.utilities.parser import parse
from aws_lambda_powertools.utilities.parser.envelopes import ApiGatewayEnvelope
from aws_lambda_powertools import Logger
from shared.models.invite_request import InviteRequest

logger = Logger()


@logger.inject_lambda_context(log_event=True)
def handler(event: Dict[str, Any], context: LambdaContext):
    return send_invite(event)


def send_invite(event: Dict[str, Any]):

    conn = get_connection()
    try:
        invite_request = parse(
            event=event, model=InviteRequest, envelope=ApiGatewayEnvelope
        )
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (first_name, last_name, mobile)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (
                    invite_request.first_name,
                    invite_request.last_name,
                    invite_request.mobile,
                ),
            )
            user_id = cur.fetchone()["id"]
            logger.append_keys(user_id=user_id)

            activation_code = generate_activation_code()
            logger.debug(
                "Activation code generated", extra={"activation_code": activation_code}
            )

            cur.execute(
                """
                INSERT INTO invites (user_id, activation_code)
                VALUES (%s, %s)
                """,
                (user_id, activation_code),
            )

        # Send SMS via SNS
        sns = boto3.client("sns")
        sns.publish(
            PhoneNumber=invite_request.mobile,
            Message=f"Your activation code is: {activation_code}",
        )

        conn.commit()
        return {"statusCode": 200, "body": json.dumps({"message": "Invite sent."})}

    except ValidationError as ve:
        logger.warning("Validation error", extra={"error": str(ve)})
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    except Exception as e:
        logger.exception("Unexpected error occurred", extra={"error": str(ve)})
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    finally:
        conn.close()


def generate_activation_code():
    return str(uuid.uuid4())[:8]
