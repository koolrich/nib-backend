import boto3
import psycopg
from psycopg.rows import dict_row

_cached_params = {}
_connection = None


def preload_params():
    if _cached_params:
        return _cached_params

    ssm = boto3.client("ssm")
    param_names = [
        "/nib/db/host",
        "/nib/db/name",
        "/nib/db/username",
        "/nib/db/password",
        "/nib/db/port",
    ]

    response = ssm.get_parameters(Names=param_names, WithDecryption=True)
    for param in response["Parameters"]:
        _cached_params[param["Name"]] = param["Value"]

    return _cached_params


def _open_connection(params):
    return psycopg.connect(
        host=params["/nib/db/host"],
        dbname=params["/nib/db/name"],
        user=params["/nib/db/username"],
        password=params["/nib/db/password"],
        port=params["/nib/db/port"],
        row_factory=dict_row,
    )


def get_connection():
    global _connection
    if _connection is None or _connection.closed:
        _connection = _open_connection(preload_params())
        return _connection
    try:
        _connection.execute("SELECT 1")
        return _connection
    except Exception:
        _connection = _open_connection(preload_params())
        return _connection
