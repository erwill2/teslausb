import pytest
import sys
import pytest_asyncio
from unittest.mock import AsyncMock, patch

import run.send_matrix as send_matrix
from nio import LoginResponse, LoginError

@pytest.fixture
def mock_client():
    with patch('run.send_matrix.AsyncClient') as mock_client_cls:
        mock_instance = mock_client_cls.return_value
        mock_instance.login = AsyncMock()
        mock_instance.room_send = AsyncMock()
        mock_instance.sync = AsyncMock()
        yield mock_client_cls

def test_main_missing_arguments(capsys):
    with patch.object(sys, 'argv', ['run/send_matrix.py']):
        with pytest.raises(SystemExit) as e:
            send_matrix.main()

        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "usage:" in captured.err

@pytest.mark.asyncio
async def test_send_message_success(mock_client):
    # Mock successful login
    mock_instance = mock_client.return_value
    mock_instance.login.return_value = LoginResponse(
        user_id="@user:example.com",
        device_id="device1",
        access_token="token"
    )

    await send_matrix.send_message(
        homeserver="https://matrix.org",
        username="user",
        password="password123",
        room_id="!room:matrix.org",
        message="Hello World"
    )

    # Verify AsyncClient initialized correctly
    mock_client.assert_called_once_with("https://matrix.org", "user")

    # Verify login
    mock_instance.login.assert_called_once()
    assert mock_instance.login.call_args[0][0] == "password123"
    assert "device_name" in mock_instance.login.call_args[1]

    # Verify message sent
    mock_instance.room_send.assert_called_once_with(
        room_id="!room:matrix.org",
        message_type="m.room.message",
        content={
            "msgtype": "m.text",
            "body": "Hello World"
        }
    )

    # Verify sync
    mock_instance.sync.assert_called_once_with(timeout=30000)

@pytest.mark.asyncio
async def test_send_message_hostname_and_username_sanitization(mock_client):
    mock_instance = mock_client.return_value
    mock_instance.login.return_value = LoginResponse(
        user_id="@user:example.com",
        device_id="device1",
        access_token="token"
    )

    await send_matrix.send_message(
        homeserver="https://matrix.org/", # Trailing slash
        username="@user:example.com",      # Leading @ and domain
        password="password123",
        room_id="!room:matrix.org",
        message="Hello World"
    )

    # Verify sanitized inputs
    mock_client.assert_called_once_with("https://matrix.org", "user")

@pytest.mark.asyncio
async def test_send_message_login_failure(mock_client, capsys):
    mock_instance = mock_client.return_value
    # Simulate failed login (returns LoginError instead of LoginResponse)
    mock_instance.login.return_value = LoginError(
        message="Invalid password",
        status_code=403
    )

    with pytest.raises(SystemExit) as e:
        await send_matrix.send_message(
            homeserver="https://matrix.org",
            username="user",
            password="wrong_password",
            room_id="!room:matrix.org",
            message="Hello World"
        )

    assert e.value.code == 1
    captured = capsys.readouterr()
    assert "Failed to connect to Matrix server." in captured.err
