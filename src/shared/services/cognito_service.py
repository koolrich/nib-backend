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
def sign_up(mobile: str, password: str) -> tuple[str, str]:
    """Returns (username, cognito_sub). UUID username is used for admin operations; sub is stored in DB."""
    import uuid as _uuid
    config = _get_cognito_config()
    client = _get_client()

    username = str(_uuid.uuid4())
    response = client.sign_up(
        ClientId=config["/nib/cognito/app_client_id"],
        Username=username,
        Password=password,
        UserAttributes=[{"Name": "phone_number", "Value": mobile}],
    )
    return username, response["UserSub"]


@tracer.capture_method(name="CognitoConfirmSignUp")
def confirm_sign_up(username: str):
    config = _get_cognito_config()
    client = _get_client()
    user_pool_id = config["/nib/cognito/user_pool_id"]

    client.admin_confirm_sign_up(
        UserPoolId=user_pool_id,
        Username=username,
    )

    client.admin_update_user_attributes(
        UserPoolId=user_pool_id,
        Username=username,
        UserAttributes=[{"Name": "phone_number_verified", "Value": "true"}],
    )


@tracer.capture_method(name="CognitoDeleteUser")
def delete_user(username: str):
    config = _get_cognito_config()
    client = _get_client()

    client.admin_delete_user(
        UserPoolId=config["/nib/cognito/user_pool_id"],
        Username=username,
    )


@tracer.capture_method(name="CognitoRefreshAuth")
def refresh_auth(refresh_token: str) -> dict:
    config = _get_cognito_config()
    client = _get_client()

    response = client.initiate_auth(
        ClientId=config["/nib/cognito/app_client_id"],
        AuthFlow="REFRESH_TOKEN_AUTH",
        AuthParameters={"REFRESH_TOKEN": refresh_token},
    )
    return response["AuthenticationResult"]


@tracer.capture_method(name="CognitoSetPassword")
def set_password(cognito_username: str, new_password: str):
    """Set a user's password directly (admin operation — no current password needed)."""
    config = _get_cognito_config()
    client = _get_client()
    client.admin_set_user_password(
        UserPoolId=config["/nib/cognito/user_pool_id"],
        Username=cognito_username,
        Password=new_password,
        Permanent=True,
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
