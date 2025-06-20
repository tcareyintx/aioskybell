"""The device class used by AIOSkybell."""
from __future__ import annotations

import logging
from datetime import datetime
from base64 import b64decode
from typing import TYPE_CHECKING, Any, cast

import aiofiles
from ciso8601 import parse_datetime  # pylint:disable=no-name-in-module

from . import utils as UTILS
from .exceptions import SkybellException
from .helpers import const as CONST
from .helpers import errors as ERROR

from .helpers.models import (  # isort:skip
    SnapshotData,
    DeviceData,
    ActivityData,
    ActivityType,
    SettingsData
)
from aioskybell.helpers.const import DEVICE_UPTIME, RESPONSE_ROWS

if TYPE_CHECKING:
    from . import Skybell

_LOGGER = logging.getLogger(__name__)


class SkybellDevice:  # pylint:disable=too-many-public-methods, too-many-instance-attributes
    """Class to represent each Skybell device."""

    _skybell: Skybell

    def __init__(self, device_json: DeviceData, skybell: Skybell) -> None:
        """Set up Skybell device."""
        self._activities: list[ActivityData] = []
        self._snapshot_json = SnapshotData()
        self._device_id = device_json.get(CONST.DEVICE_ID, "")
        self._device_json = device_json
        self._skybell = skybell
        self._type = device_json.get(CONST.TYPE, "")
        self.images: dict[str, bytes | None] = {CONST.ACTIVITY: None}
        self._events: ActivityType = {}

    async def _async_device_request(self) -> DeviceData:
        url = str.replace(CONST.DEVICE_URL, "$DEVID$", self.device_id)
        return await self._skybell.async_send_request(url)

    async def _async_snapshot_request(self) -> SnapshotData:
        url = str.replace(CONST.DEVICE_SNAPSHOT_URL, "$DEVID$", self.device_id)
        return await self._skybell.async_send_request(url)

    async def _async_settings_request(
        self,
        json: dict[str, str | int] | None = None,
        **kwargs: Any,
    ) -> SettingsData:
        url = str.replace(CONST.DEVICE_SETTINGS_URL, "$DEVID$", self.device_id)
        return await self._skybell.async_send_request(url, json=json, **kwargs)

    async def _async_activities_request(self) -> list[ActivityData]:
        """ Activities returns a list of all activity on the device
            Note that the activities is limited to default limit 
            as pagination is not supported in the activities request
        """
        url = str.replace(CONST.DEVICE_ACTIVITIES_URL, "$DEVID$", self.device_id)
        response = await self._skybell.async_send_request(url)
        return response.get(RESPONSE_ROWS,[])

    async def async_update(  # pylint:disable=too-many-arguments
        self,
        device_json: dict[str, str | dict[str, str]] | None = None,
        snapshot_json: dict[str, str] | None = None,
        refresh: bool = True,
        get_devices: bool = False,
    ) -> None:
        """Update the internal device json data."""
        if refresh or device_json or len(self._device_json) == 0:
            if get_devices:
                device_json = await self._async_device_request()
            UTILS.update(self._device_json, device_json or {})

        # The Snapshot image is the avatar of the doorbell
        if refresh or snapshot_json or len(self._snapshot_json) == 0:
            result = await self._async_snapshot_request()
            # Update the image for the avatar snapshot
            if result[CONST.PREVIEW_CREATED_AT] != self._snapshot_json.get(CONST.PREVIEW_CREATED_AT):
                base64_string = result[CONST.PREVIEW_IMAGE]
                self.images[CONST.SNAPSHOT] = b64decode(base64_string)
            self._snapshot_json = result
            UTILS.update(self._snapshot_json, snapshot_json or {})
        

        if refresh:
            await self._async_update_activities()

    async def _async_update_activities(self) -> None:
        """Update stored activities and update caches as required."""
        self._activities = await self._async_activities_request()
        _LOGGER.debug("Device Activities Response: %s", self._activities)

        # Update the selected events from the activity list
        await self._async_update_events()

        # Update the images for the activity
        if url := self.latest().get(CONST.VIDEO_URL, ""):
            if len(url) > 0:
                url = CONST.BASE_API_URL + url
                response = await self._skybell.async_send_request(url)
                url = response.get(CONST.DOWNLOAD_URL, "")
                if len(url) > 0:
                    response = await self._skybell.async_send_request(url)
                    self.images[CONST.ACTIVITY] = response

    async def _async_update_events(
        self, activities: list[ActivityData] | None = None
    ) -> None:
        """Update our cached list of latest activity events by type."""
        activities = activities or self._activities
        for activity in activities:
            event_type = activity[CONST.EVENT_TYPE]
            event_time = activity[CONST.EVENT_TIME]

            if not (old := self._events.get(event_type)) or event_time >= old[CONST.EVENT_TIME]:
                self._events[event_type] = activity

    def activities(self, limit: int = 1, event: str | None = None) -> list[ActivityData]:
        """Return device activity information."""
        activities = self._activities

        # Filter our activity array if requested
        if event:
            activities = list(filter(lambda act: act[CONST.EVENT_TYPE] == event, activities))

        # Return the requested number
        return activities[:limit]

    def latest(self, event: str | None = None) -> ActivityData:
        """Return the latest event activity."""
        _LOGGER.debug(self._events)

        # The event (e.g. button, motion is passed
        # TODO Fix the event names in routine
        if event:
            _evt: dict[str, str]
            if not (_evt := self._events.get(f"device:sensor:{event}", {})):
                _default = {CONST.EVENT_TIME: "1970-01-01T00:00:00.000Z"}
                _evt = self._events.get(f"application:on-{event}", _default)
            _entry = {CONST.EVENT_TIME: parse_datetime(_evt[CONST.EVENT_TIME])}
            return cast(ActivityData, _evt | _entry)

        latest: ActivityData = ActivityData()
        latest_date = None
        for evt in self._events.values():
            date = evt[CONST.EVENT_TIME]
            if len(latest) == 0 or latest_date is None or latest_date < date:
                latest = evt
                latest_date = date
        return latest

    async def async_set_setting(
        self, key: str, value: bool | str | int | tuple[int, int, int]
    ) -> None:
        """ Set an attribute for the device.
            The key isn't necessarily equal to the corresponding field
            and may require transformation logic.
        """
        #TODO: Validate these entries
        if key in [CONST.DO_NOT_DISTURB, CONST.DO_NOT_RING]:
            await self._async_set_setting({key: str(value)})
        if key == ("motion_sensor" or CONST.MOTION_POLICY):
            key = CONST.MOTION_POLICY
            value = bool(value)
            value = CONST.MOTION_POLICY_ON if value is True else CONST.MOTION_POLICY_OFF
            await self._async_set_setting({key: value})
        if key == CONST.RGB_COLOR:
            if not isinstance(value, (list, tuple)) or not all(
                isinstance(item, int) for item in value
            ):
                raise SkybellException(self, value)

            await self._async_set_setting(
                {
                    CONST.LED_R: value[0],
                    CONST.LED_G: value[1],
                    CONST.LED_B: value[2],
                }
            )
        if key in [
            CONST.OUTDOOR_CHIME,
            CONST.MOTION_THRESHOLD,
            CONST.VIDEO_PROFILE,
            CONST.BRIGHTNESS,
            "brightness",
        ] and not isinstance(value, tuple):
            key = CONST.BRIGHTNESS if key == "brightness" else key
            await self._async_set_setting({key: int(value)})

    async def _async_set_setting(self, settings: dict[str, str | int]) -> None:
        """Validate the settings and then send the POST request."""
        for key, value in settings.items():
            _validate_setting(key, value)

        try:
            await self._async_settings_request(
                json=settings, method=CONST.HTTPMethod.POST
            )
        except SkybellException:
            _LOGGER.warning("Exception changing settings: %s", settings)

    async def async_get_activity_video_url(self, video: str | None = None) -> str:
        """Get activity video. Return latest if no video specified."""
        act_url = str.replace(CONST.ACTIVITY_VIDEO_URL, "$ACTID$", video or self.latest()[CONST.ACTIVITY_ID])
        response = await self._skybell.async_send_request(act_url)
        return response.get(CONST.DOWNLOAD_URL, "")

    async def async_download_videos(
        self,
        path: str | None = None,
        video: str | None = None,
        limit: int = 1,
        delete: bool = False,
    ) -> None:
        """Download videos to specified path."""
        _path = self._skybell._cache_path[:-7]  # pylint:disable=protected-access
        if video and (_id := [ev for ev in self._activities if video == ev[CONST.VIDEO_URL]]):
            return await self._async_save_video(path or _path, _id[0], delete)
        for event in self.activities(limit=limit):
            await self._async_save_video(path or _path, event, delete)

    async def _async_save_video(
        self, path: str, event: ActivityData, delete: bool
    ) -> None:
        """Write video from S3 to file."""
        async with aiofiles.open(f"{path}_{event[CONST.EVENT_TIME]}.mp4", "wb") as file:
            url = await self.async_get_activity_video_url(event[CONST.VIDEO_URL])
            await file.write(await self._skybell.async_send_request(url))
        if delete:
            await self.async_delete_video(event[CONST.VIDEO_URL])

    async def async_delete_video(self, video: str) -> None:
        """Delete video with specified activity id."""
        act_url = str.replace(CONST.ACTIVITY_VIDEO_URL, "$ACTID$", video)
        await self._skybell.async_send_request(act_url, method=CONST.HTTPMethod.DELETE)

    @property
    def user_id(self) -> str:
        """Get user id that owns the device."""
        return self._device_json.get(CONST.DEVICE_OWNER, "")

    @property
    def mac(self) -> str | None:
        """Get device mac address."""
        device_settings = self._device_json.get(CONST.DEVICE_SETTINGS, {})
        return device_settings.get(CONST.DEVICE_MAC, "")

    @property
    def serial_no(self) -> str:
        """Get device serial number."""
        device_settings = self._device_json.get(CONST.DEVICE_SETTINGS, {})
        return device_settings.get(CONST.DEVICE_SERIAL_NO, "")

    @property
    def firmware_ver(self) -> str:
        """Get device firmware version."""
        device_settings = self._device_json.get(CONST.DEVICE_SETTINGS, {})
        return device_settings.get(CONST.DEVICE_FIRMWARE_VERS, "")

    @property
    def name(self) -> str:
        """Get device name."""
        return self._device_json.get(CONST.DEVICE_NAME,"")

    @property
    def type(self) -> str:
        """Get device type."""
        return self._type

    @property
    def device_id(self) -> str:
        """Get the device id."""
        return self._device_id

    @property
    def status(self) -> str:
        """Get the generic status of a device (up/down)."""
        if self.is_up:
            return CONST.STATUS_UP
        else:
            return CONST.STATUS_DOWN

    @property
    def is_up(self) -> bool:
        """Shortcut to get if the device status is up."""
        ld = self._device_json.get(CONST.LAST_DISCONNECTED, datetime(1970, 1, 1))
        lc = self._device_json.get(CONST.LAST_CONNECTED, datetime(1970, 1, 1))
        
        return lc > ld

    @property
    def location(self) -> tuple[str, str]:
        """Return lat and lng tuple."""
        return (
            self._device_json.get(CONST.LOCATION_LAT, "0"),
            self._device_json.get(CONST.LOCATION_LON, "0"),
        )

    @property
    def wifi_status(self) -> str:
        """Get the wifi status."""
        telemetry = self._device_json.get(CONST.DEVICE_TELEMETRY,{})
        return telemetry.get(CONST.WIFI_LINK_QUALITY, "")

    @property
    def wifi_ssid(self) -> str:
        """Get the wifi ssid."""
        return self._device_json.get(CONST.WIFI_SSID, "")

    @property
    def last_connected(self) -> datetime:
        """Get last connected timestamp."""
        tss = self._device_json.get(CONST.LAST_CONNECTED, "")
        try:
            ts = datetime.fromisoformat(tss)
        except ValueError:
            ts = ""
        return ts
    
    @property
    def last_check_in(self) -> datetime:
        """Get last checkin timestamp."""
        tss = self._device_json.get(CONST.UPDATED_AT, "")
        try:
            ts = datetime.fromisoformat(tss)
        except ValueError:
            ts = ""
        return ts

    @property
    def do_not_disturb(self) -> bool:
        """Get if do not disturb is enabled."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.DO_NOT_DISTURB) == "true"

    @property
    def do_not_ring(self) -> bool:
        """Get if do not ring is enabled."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.DO_NOT_RING) == "true"

    @property
    def outdoor_chime_level(self) -> int:
        """Get devices outdoor chime level."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return int(settings_json.get(CONST.OUTDOOR_CHIME, "0"))

    @property
    def outdoor_chime(self) -> bool:
        """Get if the devices outdoor chime is enabled."""
        return self.outdoor_chime_level is not CONST.OUTDOOR_CHIME_OFF

    @property
    def motion_sensor(self) -> bool:
        """Get if the devices motion sensor is enabled."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.MOTION_POLICY) == CONST.MOTION_POLICY_ON

    @property
    def motion_threshold(self) -> int:
        """Get devices motion threshold."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return int(settings_json.get(CONST.MOTION_THRESHOLD, "0"))

    @property
    def video_profile(self) -> int:
        """Get devices video profile."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return int(settings_json.get(CONST.VIDEO_PROFILE, "0"))

    @property
    def led_rgb(self) -> tuple[int, int, int]:
        """Get devices LED color."""
        #TODO Update to led_color
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return (
            int(settings_json.get(CONST.LED_R, 0)),
            int(settings_json.get(CONST.LED_G, 0)),
            int(settings_json.get(CONST.LED_B, 0)),
        )

    @property
    def led_intensity(self) -> int:
        """Get devices LED intensity."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return int(settings_json.get(CONST.BRIGHTNESS, "0"))

    @property
    def desc(self) -> str:
        """Get a short description of the device."""
        # Front Door (id: ) - skybell hd - status: up - wifi status: good
        string = f"{self.name} (id: {self.device_id}) - {self.type}"
        return f"{string} - status: {self.status} - wifi status: {self.wifi_status}"


def _validate_setting(  # pylint:disable=too-many-branches
    setting: str, value: str | int
) -> None:
    """Validate the setting and value."""
    if setting == CONST.DO_NOT_DISTURB:
        if value not in CONST.BOOL_STRINGS:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.DO_NOT_RING:
        if value not in CONST.BOOL_STRINGS:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.OUTDOOR_CHIME:
        if value not in CONST.OUTDOOR_CHIME_VALUES:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.MOTION_THRESHOLD:
        if value not in CONST.MOTION_THRESHOLD_VALUES:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.VIDEO_PROFILE:
        if value not in CONST.VIDEO_PROFILE_VALUES:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting in CONST.LED_COLORS:
        if not CONST.LED_VALUES[0] <= int(value) <= CONST.LED_VALUES[1]:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.BRIGHTNESS:
        if not CONST.BRIGHTNESS_VALUES[0] <= int(value) <= CONST.BRIGHTNESS_VALUES[1]:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))
