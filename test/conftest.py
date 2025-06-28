import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_db():
    mock_cursor = MagicMock()
    mock_cursor.execute.return_value = None
    mock_cursor.fetchone.return_value = {"id": "12345678-1234-5678-1234-567812345678"}
    mock_cursor.close.return_value = None

    mock_conn = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_conn.commit.return_value = None
    mock_conn.close.return_value = None

    return mock_conn


@pytest.fixture
def mock_sns():
    mock_sns_client = MagicMock()
    mock_sns_client.publish.return_value = {}
    return mock_sns_client
