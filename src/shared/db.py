import boto3
import psycopg
from psycopg.rows import dict_row

_cached_params = {}


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


def get_connection():
    params = preload_params()
    return psycopg.connect(
        host=params["/nib/db/host"],
        dbname=params["/nib/db/name"],
        user=params["/nib/db/username"],
        password=params["/nib/db/password"],
        port=params["/nib/db/port"],
        row_factory=dict_row,
    )
