from unittest.mock import patch, MagicMock
from shared import db


@patch("shared.db.boto3.client")
def test_preload_params(mock_boto):
    mock_ssm = MagicMock()
    mock_boto.return_value = mock_ssm
    mock_ssm.get_parameters.return_value = {
        "Parameters": [
            {"Name": "/nib/db/host", "Value": "localhost"},
            {"Name": "/nib/db/name", "Value": "testdb"},
            {"Name": "/nib/db/username", "Value": "testuser"},
            {"Name": "/nib/db/password", "Value": "testpass"},
            {"Name": "/nib/db/port", "Value": "5432"},
        ]
    }

    result = db.preload_params()
    assert result["/nib/db/host"] == "localhost"
    assert result["/nib/db/name"] == "testdb"
    assert result["/nib/db/username"] == "testuser"
    assert result["/nib/db/password"] == "testpass"
    assert result["/nib/db/port"] == "5432"


@patch("shared.db.psycopg.connect")
@patch("shared.db.preload_params")
def test_get_connection(mock_preload, mock_connect):
    mock_preload.return_value = {
        "/nib/db/host": "localhost",
        "/nib/db/name": "testdb",
        "/nib/db/username": "testuser",
        "/nib/db/password": "testpass",
        "/nib/db/port": "5432",
    }

    conn = MagicMock()
    mock_connect.return_value = conn

    result = db.get_connection()
    mock_preload.assert_called_once()
