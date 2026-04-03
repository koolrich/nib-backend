import boto3

from shared.instrumentation.tracer import tracer
from aws_lambda_powertools import Logger

logger = Logger()

_cognito_params = {}
_cognito_client = None


def _get_cognito_config():
    if _cognito_params:
        return _cognito_params

    ssm = boto3.client("ssm")
    response = ssm.get_parameters(
        Names=["/nib/cognito/user_pool_id", "/nib/cognito/app_client_id"],
        WithDecryption=False,
    )
    for param in response["Parameters"]:
        _cognito_params[param["Name"]] = param["Value"]

    return _cognito_params


def _get_client():
    global _cognito_client
    if _cognito_client is None:
        _cognito_client = boto3.client("cognito-idp")
    return _cognito_client


@tracer.capture_method(name="CognitoSignUp")
def sign_up(mobile: str, password: str) -> str:
    """Returns cognito_sub. A UUID is used as the Cognito username; sub is used for all subsequent admin operations."""
    import uuid as _uuid
    config = _get_cognito_config()
    client = _get_client()

    response = client.sign_up(
        ClientId=config["/nib/cognito/app_client_id"],
        Username=str(_uuid.uuid4()),
        Password=password,
        UserAttributes=[{"Name": "phone_number", "Value": mobile}],
    )
    return response["UserSub"]


@tracer.capture_method(name="CognitoConfirmSignUp")
def confirm_sign_up(cognito_sub: str):
    config = _get_cognito_config()
    client = _get_client()

    client.admin_confirm_sign_up(
        UserPoolId=config["/nib/cognito/user_pool_id"],
        Username=cognito_sub,
    )


@tracer.capture_method(name="CognitoDeleteUser")
def delete_user(cognito_sub: str):
    config = _get_cognito_config()
    client = _get_client()

    client.admin_delete_user(
        UserPoolId=config["/nib/cognito/user_pool_id"],
        Username=cognito_sub,
    )


@tracer.capture_method(name="CognitoInitiateAuth")
def initiate_auth(mobile: str, password: str) -> dict:
    config = _get_cognito_config()
    client = _get_client()

    response = client.admin_initiate_auth(
        UserPoolId=config["/nib/cognito/user_pool_id"],
        ClientId=config["/nib/cognito/app_client_id"],
        AuthFlow="ADMIN_USER_PASSWORD_AUTH",
        AuthParameters={
            "USERNAME": mobile,
            "PASSWORD": password,
        },
    )
    return response["AuthenticationResult"]
