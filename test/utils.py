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


def generate_api_gw_event(
    body: Optional[dict[str, Any]],
    cognito_sub: Optional[str] = "test-cognito-sub-123",
    route_key: str = "POST /test",
    path_params: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    request_context: dict[str, Any] = {
        "accountId": "123456789012",
        "apiId": "api-id",
        "domainName": "api-id.execute-api.eu-west-2.amazonaws.com",
        "domainPrefix": "api-id",
        "stage": "dev",
        "requestId": "test-request-id",
        "routeKey": route_key,
        "time": "01/Jan/2021:12:00:00 +0000",
        "timeEpoch": 1609502400000,
        "http": {
            "method": route_key.split(" ")[0],
            "path": "/test",
            "protocol": "HTTP/1.1",
            "sourceIp": "127.0.0.1",
            "userAgent": "test",
        },
        "authorizer": {
            "jwt": {
                "claims": {"sub": cognito_sub}
            }
        },
    }

    return {
        "version": "2.0",
        "routeKey": route_key,
        "rawPath": "/test",
        "rawQueryString": "",
        "headers": {"content-type": "application/json"},
        "requestContext": request_context,
        "pathParameters": path_params or {},
        "body": "" if body is None else json.dumps(body),
        "isBase64Encoded": False,
    }
