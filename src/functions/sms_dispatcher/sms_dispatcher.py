import json
import os
from base64 import b64encode

import boto3
import urllib.request
import urllib.error
import urllib.parse

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

from shared.instrumentation.tracer import tracer

logger = Logger()

_ssm = boto3.client("ssm")
_twilio_account_sid = None
_twilio_auth_token = None
_twilio_from_number = None

_env = os.environ["ENV"]
_SSM_PREFIX = f"/nib/{_env}/twilio"


def _load_twilio_config():
    global _twilio_account_sid, _twilio_auth_token, _twilio_from_number
    if _twilio_account_sid:
        return
    params = _ssm.get_parameters(
        Names=[
            f"{_SSM_PREFIX}/account_sid",
            f"{_SSM_PREFIX}/auth_token",
            f"{_SSM_PREFIX}/from_number",
        ],
        WithDecryption=True,
    )
    by_name = {p["Name"]: p["Value"] for p in params["Parameters"]}
    _twilio_account_sid = by_name[f"{_SSM_PREFIX}/account_sid"]
    _twilio_auth_token = by_name[f"{_SSM_PREFIX}/auth_token"]
    _twilio_from_number = by_name[f"{_SSM_PREFIX}/from_number"]


def _send_sms(mobile: str, message: str):
    _load_twilio_config()
    url = f"https://api.twilio.com/2010-04-01/Accounts/{_twilio_account_sid}/Messages.json"
    credentials = b64encode(f"{_twilio_account_sid}:{_twilio_auth_token}".encode()).decode()
    data = urllib.parse.urlencode({
        "To": mobile,
        "From": _twilio_from_number,
        "Body": message,
    }).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            body = json.loads(resp.read())
            logger.info("SMS sent", extra={"sid": body.get("sid"), "status": body.get("status")})
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        logger.error("Twilio request failed", extra={"status": e.code, "body": error_body})
        raise RuntimeError(f"Twilio SMS failed: {e.code} {error_body}")


@logger.inject_lambda_context(log_event=True)
@tracer.capture_lambda_handler
def handler(event, context: LambdaContext):
    for record in event.get("Records", []):
        payload = json.loads(record["Sns"]["Message"])
        mobile = payload["mobile"]
        message = payload["message"]
        logger.info("Dispatching SMS", extra={"mobile": mobile})
        _send_sms(mobile, message)
