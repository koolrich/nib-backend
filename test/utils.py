from typing import Any, Optional
from aws_lambda_powertools.utilities.typing import LambdaContext
from unittest.mock import MagicMock
import json


def generate_context():
    context = MagicMock()
    context.function_name = "send_invite"
    context.function_version = "1"
    context.aws_request_id = "test-id"
    return context


def generate_api_gw_event(body: Optional[dict[str, Any]]) -> dict[str, Any]:
    return {
        "resource": "/send-invite",
        "path": "/send-invite",
        "httpMethod": "POST",
        "headers": {},
        "multiValueHeaders": {},
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "api-id",
            "stage": "dev",
            "protocol": "HTTP/1.1",
            "identity": {"sourceIp": "127.0.0.1"},
            "requestId": "test-request-id",
            "requestTime": "01/Jan/2021:12:00:00 +0000",
            "requestTimeEpoch": 1609502400000,
            "resourcePath": "/send-invite",
            "httpMethod": "POST",
            "path": "/dev/send-invite",
        },
        "body": "" if body is None else json.dumps(body),
        "isBase64Encoded": False,
    }
