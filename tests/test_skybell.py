# pylint:disable=line-too-long, protected-access, too-many-statements
"""
Test Skybell device functionality.

Tests the device initialization and attributes of the Skybell device class.
"""
import asyncio
import datetime as dt
import os
from asyncio.exceptions import TimeoutError as Timeout
from unittest.mock import patch

import aiofiles
import pytest
from aiohttp import ClientConnectorError
from aresponses import ResponsesMockServer
from freezegun.api import FrozenDateTimeFactory

from aioskybell import Skybell, exceptions
from aioskybell import utils as UTILS
from aioskybell.device import SkybellDevice
from aioskybell.helpers import const as CONST
from tests import EMAIL, PASSWORD, load_fixture


def login_response(aresponses: ResponsesMockServer) -> None:
    """Generate login response."""
    aresponses.add(
        "api.skybell.network",
        "/api/v5/login/",
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("login.json"),
        ),
    )


def user_response(aresponses: ResponsesMockServer) -> None:
    """Generate login response."""
    aresponses.add(
        "api.skybell.network",
        "/api/v5/user/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("user.json"),
        ),
    )


def failed_login_response(aresponses: ResponsesMockServer) -> None:
    """Generate failed login response."""
    aresponses.add(
        "api.skybell.network",
        "/api/v5/login/",
        "POST",
        aresponses.Response(
            status=403,
            headers={"Content-Type": "application/json"},
            text=load_fixture("403.json"),
        ),
    )


def devices_response(aresponses: ResponsesMockServer) -> None:
    """Generate devices response."""
    aresponses.add(
        "api.skybell.network",
        "/api/v5/devices/",
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("devices.json"),
        ),
    )


@pytest.mark.asyncio
async def test_loop() -> None:
    """Test loop usage is handled correctly."""
    async with Skybell(EMAIL, PASSWORD) as skybell:
        assert isinstance(skybell, Skybell)
        cemail = EMAIL.replace(".", "")
        assert skybell._cache_path == f"skybell_{cemail}.pickle"


@pytest.mark.asyncio
async def test_async_initialize_and_logout(aresponses: ResponsesMockServer) -> None:
    """Test initializing and logout."""
    client = Skybell(
        EMAIL, PASSWORD, auto_login=True, get_devices=True, login_sleep=False
    )
    login_response(aresponses)
    user_response(aresponses)
    devices_response(aresponses)
    data = await client.async_initialize()
    assert client.user_id == "1234567890abcdef12345678"
    assert client.user_first_name == "First"
    assert client.user_last_name == "Last"
    assert client._cache["AuthenticationResult"]
    ar = client._cache["AuthenticationResult"]
    assert ar["AccessToken"] == "superlongkey"
    with pytest.raises(KeyError):
        client._cache["devices"]

    assert isinstance(data[0], SkybellDevice)
    device = client._devices["012345670123456789abcdef"]
    assert isinstance(device, SkybellDevice)

    assert await client.async_logout() is True
    assert not client._devices

    assert await client.async_login() is False

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, os.remove(client._cache_path))

    assert not aresponses.assert_no_unused_routes()