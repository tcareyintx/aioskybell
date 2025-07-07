# pylint:disable=line-too-long, protected-access, too-many-statements
"""
Test Skybell device functionality.

Tests the device initialization and attributes of the Skybell device class.
"""
import asyncio
import os
from datetime import datetime
from asyncio.exceptions import TimeoutError as Timeout
from unittest.mock import patch

import aiofiles
import pytest
from aiohttp import ClientConnectorError
from aresponses import ResponsesMockServer
from freezegun.api import FrozenDateTimeFactory

from aioskybell import Skybell, exceptions
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


def refresh_response(aresponses: ResponsesMockServer) -> None:
    """Generate refresh session response."""
    aresponses.add(
        "api.skybell.network",
        "/api/v5/token/",
        "PUT",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("refresh_session.json"),
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


def device_response(aresponses: ResponsesMockServer, device: str) -> None:
    """Generate devices response."""
    path = f"/api/v5/devices/{device}/"
    aresponses.add(
        "api.skybell.network",
        path,
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("device.json"),
        ),
    )


def snapshot_response(aresponses: ResponsesMockServer, device: str) -> None:
    """Generate snapshot response."""
    path = f"/api/v5/devices/{device}/snapshot/"
    aresponses.add(
        "api.skybell.network",
        path,
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("device_snapshot.json"),
        ),
    )


def activities_response(aresponses: ResponsesMockServer, device: str) -> None:
    """Generate snapshot response."""
    path = f"/api/v5/activity?device_id={device}&nopreviews=0"
    aresponses.add(
        "api.skybell.network",
        path,
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("device_activities.json"),
        ),
        match_querystring=True,
    )


def device_settings_response(
        aresponses: ResponsesMockServer,
        device: str
) -> None:
    """Generate device settings response."""
    path = f"/api/v5/devices/{device}/settings/"
    aresponses.add(
        "api.skybell.network",
        path,
        "POST",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("device-settings.json"),
        ),
    )


def download_video_url_response(
        aresponses: ResponsesMockServer,
        video_id: str
) -> None:
    """Generate device settings response."""
    path = f"/api/v5{video_id}"
    aresponses.add(
        "api.skybell.network",
        path,
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("video_url.json"),
        ),
    )


def delete_activity_response(
        aresponses: ResponsesMockServer,
        activity: str
) -> None:
    """Generate device settings response."""
    path = f"/api/v5/activity/{activity}"
    aresponses.add(
        "api.skybell.network",
        path,
        "DELETE",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "application/json"},
            text=load_fixture("video_url.json"),
        ),
    )


def get_video_response(
        aresponses: ResponsesMockServer,
        video: str
) -> None:
    """Generate device settings response."""
    aresponses.add(
        "skybell-gen5-video.s3.us-east-2.amazonaws.com",
        video,
        "GET",
        aresponses.Response(
            status=200,
            headers={"Content-Type": "binary/octet-stream"},
            body=bytes(2)
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
async def test_async_initialize_and_logout(
    aresponses: ResponsesMockServer
) -> None:
    """Test initializing and logout."""
    client = Skybell(
        EMAIL, PASSWORD, auto_login=True, get_devices=True, login_sleep=False
    )
    login_response(aresponses)
    user_response(aresponses)
    devices_response(aresponses)
    refresh_response(aresponses)
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
    assert isinstance(device.skybell, Skybell)

    # Test the session refresh
    await client.async_refresh_session()
    ar = client._cache["AuthenticationResult"]
    assert ar["AccessToken"] == "LongToken"
    assert ar["ExpiresIn"] == 3600
    assert client.session_refresh_period == 3600
    assert ar["TokenType"] == "Bearer"
    assert isinstance(ar["ExpirationDate"], datetime)
    assert isinstance(client.session_refresh_timestamp, datetime)

    # Test the session logout
    assert await client.async_logout() is True
    assert not client._devices

    with pytest.raises(RuntimeError):
        await client.async_login()

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, os.remove(client._cache_path))

    assert not aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_async_get_devices(
    aresponses: ResponsesMockServer,
    client: Skybell,
    freezer: FrozenDateTimeFactory
) -> None:
    """Test getting devices."""
    freezer.move_to("2023-03-30 13:33:00+00:00")
    login_response(aresponses)
    devices_response(aresponses)

    # Test the Get Device and device specific attributes
    data = await client.async_get_device("012345670123456789abcdef",
                                         refresh=True)
    assert isinstance(data, SkybellDevice)
    device = client._devices["012345670123456789abcdef"]
    assert isinstance(device, SkybellDevice)
    # Test public API and device data structure
    assert device._device_json["basic_motion"] == {
                    "fd_notify": True,
                    "fd_record": True,
                    "hbd_notify": True,
                    "hbd_record": True,
                    "motion_notify": True,
                    "motion_record": True
                }
    assert device.basic_motion == {
                    "fd_notify": True,
                    "fd_record": True,
                    "hbd_notify": True,
                    "hbd_record": True,
                    "motion_notify": True,
                    "motion_record": True
                }
    assert device._device_json["created_at"] == "2020-10-20T14:35:00.745Z"
    assert (
        device._device_json["invite_token"]
        == "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    )
    assert device._device_json["device_id"] == "012345670123456789abcdef"
    assert device.device_id == "012345670123456789abcdef"
    assert device._device_json["name"] == "FrontDoor"
    assert device.name == "FrontDoor"
    assert device._device_json["last_connected"] == "2020-10-21T14:35:00.745Z"
    assert device.last_connected.strftime("%Y-%m-%d") == "2020-10-21"
    assert (device._device_json["last_disconnected"] ==
            "2020-10-20T14:35:00.745Z")
    assert device.last_disconnected.strftime("%Y-%m-%d") == "2020-10-20"
    assert device._device_json["updated_at"] == "2021-10-20T14:35:00.745Z"
    assert device._device_json["account_id"] == "123-123-123"
    assert device.user_id == "123-123-123"
    assert device.is_shared is False
    assert device.is_readonly is False
    assert device.status == "Up"
    assert device.is_up is True
    assert device.desc == "FrontDoor (id: 012345670123456789abcdef) " +\
        "- SB_SLIM2_0001 - status: Up - WiFi link quality: 98/100"

    # Test public API and device settings structure
    device_settings = device._device_json["device_settings"]
    assert device_settings["model_rev"] == "SB_SLIM2_0001"
    assert device.type == "SB_SLIM2_0001"
    assert device_settings["MAC_address"] == "AA:BB:CC:DD:EE:FF"
    assert device.mac == "AA:BB:CC:DD:EE:FF"
    assert device_settings["serial_number"] == "ASERIALNUM"
    assert device.serial_no == "ASERIALNUM"
    assert device_settings["serial_number"] == "ASERIALNUM"
    assert device.serial_no == "ASERIALNUM"
    assert device_settings["firmware_version"] == "1.7.21"
    assert device.firmware_ver == "1.7.21"
    assert device_settings["ESSID"] == "SSID"

    # Test public API and device telemetry structure
    telemetry = device._device_json["telemetry"]
    assert telemetry["last_seen"] == "2022-10-20T14:35:00.745Z"
    assert device.last_seen.strftime("%Y-%m-%d") == "2022-10-20"
    assert telemetry["link_quality"] == "98/100"
    assert device.wifi_link_quality == "98/100"
    assert telemetry["signal_level"] == "-54"
    assert device.wifi_signal_level == "-54"
    assert telemetry["essid"] == "SSID"
    assert device.wifi_ssid == "SSID"

    # Test punlic API and settings structure
    settings = device._device_json["settings"]
    assert settings["time_zone_info"] == {
                            "mapLat": 1.0,
                            "mapLong": -1.0,
                            "place": "Anywhere"
                        }
    assert device.location == ("1.0", "-1.0")
    assert settings["device_name"] == "FrontDoor"
    assert settings["button_pressed"] is True
    assert device.button_pressed is True
    assert settings["led_control"] == "Normal"
    assert device.led_control == "Normal"
    assert settings["led_color"] == "#00ff00"
    assert device.led_color == "#00ff00"
    assert settings["indoor_chime"] is True
    assert device.indoor_chime is True
    assert settings["digital_chime"] is False
    assert device.digital_chime is False
    assert settings["outdoor_chime"] is True
    assert device.outdoor_chime is True
    assert settings["outdoor_chime_volume"] == 2
    assert device.outdoor_chime_volume == 2
    assert settings["speaker_volume"] == 1
    assert device.speaker_volume == 1
    assert settings["motion_detection"] is True
    assert device.motion_detection is True
    assert settings["debug_motion_detect"] is True
    assert device.debug_motion_detect is True
    assert settings["motion_sensitivity"] == 534
    assert device.motion_sensitivity == 534
    assert settings["hmbd_sensitivity"] == 500
    assert device.hmbd_sensitivity == 500
    assert settings["fd_sensitivity"] == 573
    assert device.fd_sensitivity == 573
    assert settings["pir_sensitivity"] == 524
    assert device.pir_sensitivity == 524
    assert settings["image_quality"] == 0
    assert device.image_quality == 0

    assert aresponses.assert_no_unused_routes() is None


@pytest.mark.asyncio
async def test_async_refresh_device(
    aresponses: ResponsesMockServer,
    client: Skybell,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test refreshing device."""
    freezer.move_to("2023-03-30 13:33:00+00:00")
    login_response(aresponses)
    devices_response(aresponses)
    data = await client.async_get_devices()
    device = data[0]

    # Test the update for the devices
    device_response(aresponses, device.device_id)
    snapshot_response(aresponses, device.device_id)
    activities_response(aresponses, device.device_id)
    await device.async_update(get_devices=True)
    assert device._device_json["device_id"] == "012345670123456789abcdef"
    assert device.device_id == "012345670123456789abcdef"
    assert device._device_json["name"] == "FrontDoor"
    assert device.name == "FrontDoor"

    # Test the activities for the device
    data = device.activities()[0]

    assert data["activity_id"] == "bdc15f68-4c7b-41e2-8c54-adfb800898a9"
    assert data["event_type"] == "doorbell"
    assert data["event_time"] == 1751732391135
    assert data["device_id"] == "012345670123456789abcdef"
    assert data["image"] is None
    assert data["video_ready"] is True
    assert data["video_url"] ==\
        "/activity/act-doorbell/video"

    assert isinstance(device.activities(event="motion"), list)
    assert isinstance(device.latest(event_type="motion"), dict)
    assert device.latest(event_type="motion")[CONST.CREATED_AT] ==\
        "2019-07-05T14:30:17.659Z"
    assert device.latest(event_type="doorbell")[CONST.CREATED_AT] ==\
        "2019-07-05T16:19:51.157Z"

    # Test a basic update that does not get the device
    snapshot_response(aresponses, device.device_id)
    activities_response(aresponses, device.device_id)
    await device.async_update()
    assert device._device_json["device_id"] == "012345670123456789abcdef"
    assert device.device_id == "012345670123456789abcdef"
    assert device._device_json["name"] == "FrontDoor"
    assert device.name == "FrontDoor"

    # Clear the cache file
    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, os.remove(client._cache_path))

    assert aresponses.assert_no_unused_routes() is None


@pytest.mark.asyncio
async def test_async_change_setting(
    aresponses: ResponsesMockServer, client: Skybell
) -> None:
    """Test changing settings on device."""

    login_response(aresponses)
    devices_response(aresponses)
    data = await client.async_get_devices()
    device = data[0]
    assert isinstance(device._device_json["settings"], dict)

    # Test public API and settings structure
    device_response(aresponses, device.device_id)
    snapshot_response(aresponses, device.device_id)
    activities_response(aresponses, device.device_id)
    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("name", "FrontDoor")
    settings = device._device_json["settings"]
    assert settings["device_name"] == "FrontDoor"

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("button_pressed", True)
    settings = device._device_json["settings"]
    assert settings["button_pressed"] is True

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("led_control", "Normal")
    settings = device._device_json["settings"]
    assert settings["led_control"] == "Normal"

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("led_color", "#00ff00")
    settings = device._device_json["settings"]
    assert settings["led_color"] == "#00ff00"

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("indoor_chime", True)
    settings = device._device_json["settings"]
    assert settings["indoor_chime"] is True

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("digital_chime", False)
    settings = device._device_json["settings"]
    assert settings["digital_chime"] is False

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("outdoor_chime", True)
    settings = device._device_json["settings"]
    assert settings["outdoor_chime"] is True

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("outdoor_chime_volume", 2)
    settings = device._device_json["settings"]
    assert settings["outdoor_chime_volume"] == 2

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("speaker_volume", 1)
    settings = device._device_json["settings"]
    assert settings["speaker_volume"] == 1

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("motion_detection", True)
    settings = device._device_json["settings"]
    assert settings["motion_detection"] is True

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("debug_motion_detect", True)
    settings = device._device_json["settings"]
    assert settings["debug_motion_detect"] is True

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("motion_sensitivity", 1000)
    settings = device._device_json["settings"]
    assert settings["motion_sensitivity"] == 1000

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("hmbd_sensitivity", 500)
    settings = device._device_json["settings"]
    assert settings["hmbd_sensitivity"] == 500

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("fd_sensitivity", 500)
    settings = device._device_json["settings"]
    assert settings["fd_sensitivity"] == 500

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("pir_sensitivity", 524)
    settings = device._device_json["settings"]
    assert settings["pir_sensitivity"] == 524
    assert device.pir_sensitivity == 524

    device_settings_response(aresponses, device.device_id)
    await device.async_set_setting("image_quality", 0)
    settings = device._device_json["settings"]
    assert settings["image_quality"] == 0
    assert device.image_quality == 0

    with pytest.raises(exceptions.SkybellException):
        await client.async_get_device("foo")

    # Test Range Exceptions (_validate_setting)
    # Check the enumerations
    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.OUTDOOR_CHIME_VOLUME, 4)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.SPEAKER_VOLUME, 4)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.IMAGE_QUALITY, 4)

    # Check the booleans
    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.INDOOR_CHIME, 4)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.INDOOR_DIGITAL_CHIME, 4)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.OUTDOOR_CHIME, 4)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.MOTION_DETECTION, 4)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.DEBUG_MOTION_DETECTION, 4)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.BUTTON_PRESSED, 4)

    # Check the ranges
    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.MOTION_SENSITIVITY, 1500)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.MOTION_PIR_SENSITIVITY, 1500)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.MOTION_HMBD_SENSITIVITY, 1500)

    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.MOTION_FD_SENSITIVITY, 1500)

    # Validate the basic motion fields
    motion_dict = {
        CONST.BASIC_MOTION_NOTIFY: True,
        CONST.BASIC_MOTION_RECORD: True,
        CONST.BASIC_MOTION_FD_NOTIFY: True,
        CONST.BASIC_MOTION_FD_RECORD: True,
        CONST.BASIC_MOTION_HBD_NOTIFY: True,
        CONST.BASIC_MOTION_HBD_RECORD: True,
        "invalid_field": False,
    }
    with pytest.raises(exceptions.SkybellException):
        await device.async_set_setting(CONST.BASIC_MOTION, motion_dict)

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, os.remove(client._cache_path))

    assert aresponses.assert_no_unused_routes() is None


@pytest.mark.asyncio
async def test_async_get_activity_video_url(
    aresponses: ResponsesMockServer,
    client: Skybell
) -> None:
    """Test getting the video url for an activity.
        Test simulating a download of a video.
    """

    # Get the device with its activity
    login_response(aresponses)
    devices_response(aresponses)
    data = await client.async_get_devices()
    device = data[0]

    # Test the update for the devices
    device_response(aresponses, device.device_id)
    snapshot_response(aresponses, device.device_id)
    activities_response(aresponses, device.device_id)
    await device.async_update(get_devices=True)

    # Get video url associated with an activity
    act = device.latest()
    video_id = act[CONST.VIDEO_URL]
    download_video_url_response(aresponses, video_id=video_id)
    download_url = await device.async_get_activity_video_url(video=video_id)
    assert download_url ==\
        "https://skybell-gen5-video.s3.us-east-2.amazonaws.com/video-id"

    # Download the video ( and cleanup file)
    activity_id = act[CONST.ACTIVITY_ID]
    delete_activity_response(aresponses, activity_id)
    download_video_url_response(aresponses, video_id=video_id)
    get_video_response(aresponses, "/video-id")
    await device.async_download_videos(video=download_url, delete=True)
    path = client._cache_path[:-7]
    file = f"{path}_{act[CONST.EVENT_TIME]}.mp4"
    assert os.path.exists(file) is True
    if os.path.exists(file):
        os.remove(file)

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, os.remove(client._cache_path))

    assert not aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_async_delete_activity(
    aresponses: ResponsesMockServer,
    client: Skybell
) -> None:
    """Test deleting an activity"""

    # Get the device with its activity
    login_response(aresponses)
    devices_response(aresponses)
    data = await client.async_get_devices()
    device = data[0]

    # Test the update for the devices
    device_response(aresponses, device.device_id)
    snapshot_response(aresponses, device.device_id)
    activities_response(aresponses, device.device_id)
    await device.async_update(get_devices=True)

    # Get activiry id associated with an activity
    act = device.latest()
    activity_id = act[CONST.ACTIVITY_ID]
    delete_activity_response(aresponses, activity_id)
    await device.async_delete_activity(activity_id=activity_id)
    assert len(device._activities) == 1
    assert len(device._events) == 1

    loop = asyncio.get_running_loop()
    loop.run_in_executor(None, os.remove(client._cache_path))

    assert not aresponses.assert_no_unused_routes()


@pytest.mark.asyncio
async def test_cache(
    aresponses: ResponsesMockServer,
    client: Skybell,
) -> None:
    """Test cache."""

    login_response(aresponses)
    user_response(aresponses)
    devices_response(aresponses)
    # Create the cache file
    if os.path.exists(client._cache_path):
        await os.remove(client._cache_path)

    # Load the cache and write to the file
    await client.async_initialize()

    # Test the contents of the cache file
    assert os.path.exists(client._cache_path) is True
    async with aiofiles.open(client._cache_path, mode='r') as f:
        contents = await f.read()
    assert len(contents) > 0


@pytest.mark.asyncio
async def test_async_test_ports(client: Skybell) -> None:
    """Test open ports."""
    with patch("aioskybell.ClientSession.get") as session:
        session.side_effect = ClientConnectorError("", OSError(61, ""))
        assert await client.async_test_ports("1.2.3.4") is True

    with patch("aioskybell.ClientSession.get") as session:
        session.side_effect = Timeout
        assert await client.async_test_ports("1.2.3.4") is False


@pytest.mark.asyncio
async def ckean_up_cache(client: Skybell) -> None:
    """Cleanup the cache file."""
    if os.path.exists(client._cache_path):
        await os.remove(client._cache_path)
