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
        activation_code = generate_activation_code()
        logger.debug(
            "Activation code generated", extra={"activation_code": activation_code}
        )

        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO invites (first_name, last_name, mobile, activation_code, invited_by, relationship, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    invite_request.first_name,
                    invite_request.last_name,
                    invite_request.mobile,
                    activation_code,
                    "54789478-d081-707a-8ff8-f18dc0258a3c",
                    invite_request.relationship,
                    "other",
                ),
            )

        # Send SMS via SNS

        sns = boto3.client("sns")
        response = sns.publish(
            PhoneNumber=invite_request.mobile,
            Message=f"Your activation code is: {activation_code}",
            MessageAttributes={
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",  # Or 'Promotional'
                }
            },
        )
        status_code = response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if status_code != 200:
            logger.error(
                "SMS may not have been sent successfully",
                extra={"sns_response": response},
            )

        conn.commit()
        return {"statusCode": 200, "body": json.dumps({"message": "Invite sent."})}

    except ValidationError as ve:
        logger.warning("Validation error", extra={"error": str(ve)})
        return {"statusCode": 400, "body": json.dumps({"error": str(ve)})}

    except Exception as e:
        conn.rollback()
        logger.exception("Unexpected error occurred", extra={"error": str(e)})
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}

    finally:
        conn.close()


def generate_activation_code():
    return uuid.uuid4().hex[:8].upper()
