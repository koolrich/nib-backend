import os

import boto3
import psycopg
from psycopg.rows import dict_row

_cached_params = {}
_connection = None

_env = os.environ["ENV"]
_SSM_PREFIX = f"/nib/{_env}/db"


def preload_params():
    if _cached_params:
        return _cached_params

    ssm = boto3.client("ssm")
    param_names = [
        f"{_SSM_PREFIX}/host",
        f"{_SSM_PREFIX}/name",
        f"{_SSM_PREFIX}/username",
        f"{_SSM_PREFIX}/password",
        f"{_SSM_PREFIX}/port",
    ]

    response = ssm.get_parameters(Names=param_names, WithDecryption=True)
    for param in response["Parameters"]:
        _cached_params[param["Name"]] = param["Value"]

    return _cached_params


def _open_connection(params):
    return psycopg.connect(
        host=params[f"{_SSM_PREFIX}/host"],
        dbname=params[f"{_SSM_PREFIX}/name"],
        user=params[f"{_SSM_PREFIX}/username"],
        password=params[f"{_SSM_PREFIX}/password"],
        port=params[f"{_SSM_PREFIX}/port"],
        row_factory=dict_row,
    )


def get_connection():
    global _connection
    if _connection is None or _connection.closed:
        _connection = _open_connection(preload_params())
    return _connection
