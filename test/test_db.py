from unittest.mock import patch, MagicMock
from shared import db

_PREFIX = "/nib/test/db"


@patch("shared.db.boto3.client")
def test_preload_params(mock_boto):
    mock_ssm = MagicMock()
    mock_boto.return_value = mock_ssm
    mock_ssm.get_parameters.return_value = {
        "Parameters": [
            {"Name": f"{_PREFIX}/host", "Value": "localhost"},
            {"Name": f"{_PREFIX}/name", "Value": "testdb"},
            {"Name": f"{_PREFIX}/username", "Value": "testuser"},
            {"Name": f"{_PREFIX}/password", "Value": "testpass"},
            {"Name": f"{_PREFIX}/port", "Value": "5432"},
        ]
    }

    result = db.preload_params()
    assert result[f"{_PREFIX}/host"] == "localhost"
    assert result[f"{_PREFIX}/name"] == "testdb"
    assert result[f"{_PREFIX}/username"] == "testuser"
    assert result[f"{_PREFIX}/password"] == "testpass"
    assert result[f"{_PREFIX}/port"] == "5432"


@patch("shared.db.psycopg.connect")
@patch("shared.db.preload_params")
def test_get_connection(mock_preload, mock_connect):
    mock_preload.return_value = {
        f"{_PREFIX}/host": "localhost",
        f"{_PREFIX}/name": "testdb",
        f"{_PREFIX}/username": "testuser",
        f"{_PREFIX}/password": "testpass",
        f"{_PREFIX}/port": "5432",
    }

    conn = MagicMock()
    mock_connect.return_value = conn

    result = db.get_connection()
    mock_preload.assert_called_once()
