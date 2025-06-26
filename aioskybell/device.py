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
from aioskybell.helpers.const import RESPONSE_ROWS


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
        device_settings = self._device_json.get(CONST.DEVICE_SETTINGS, {})
        self._type = device_settings.get(CONST.HARDWARE_VERSION, "")
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
        # Update the internal device json data.
        if refresh or device_json or not self._device_json:
            if get_devices:
                device_json = await self._async_device_request()
            UTILS.update(self._device_json, device_json or {})

        # The Snapshot image is the avatar of the doorbell.
        if refresh or snapshot_json or not self._snapshot_json:
            result = await self._async_snapshot_request()
            # Update the image for the avatar snapshot.
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

        # Update the selected events from the activity list.
        await self._async_update_events()

        # Update the images for the activity.
        if url := self.latest().get(CONST.VIDEO_URL, ""):
            if len(url) > 0:
                url = CONST.BASE_API_URL + url
                response = await self._skybell.async_send_request(url)
                url = response.get(CONST.DOWNLOAD_URL, "")
                if not url:
                    response = await self._skybell.async_send_request(url)
                    self.images[CONST.ACTIVITY] = response

    async def _async_update_events(
        self, activities: list[ActivityData] | None = None
    ) -> None:
        #Update our cached list of latest activity events by type.
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
            if not latest or latest_date is None or latest_date < date:
                latest = evt
                latest_date = date
        return latest

    async def async_set_setting(
        self, key: str, value: bool | str | int | tuple[int, int, int]
    ) -> None:
        # Set an attribute for the device.
        # The key isn't necessarily equal to the corresponding field
        # and may require transformation logic.
        if key == CONST.LED_COLOR:
            if not isinstance(value, (list, tuple)) or not all(
                isinstance(item, int) for item in value
            ):
                raise SkybellException(self, value)

            rgb_value = "#{0:02x}{1:02x}{2:02x}".format(value[0], value[1], value[2])
            return await self._async_set_setting({key: rgb_value})
        
        # Normal LED control of false has to reset the LED COLOR to Empty
        if key == CONST.NORMAL_LED:
            if not isinstance(value, bool):
                raise SkybellException(self, value)
            key = CONST.LED_COLOR
            if value:
                rgb = self.led_color
                value = "#{0:02x}{1:02x}{2:02x}".format(rgb[0], rgb[1], rgb[2])
                if not value:
                    value = CONST.DEFAULT_NORMAL_LED_COLOR
            else:
                value = ""

 
        # UPdate the settings value for the key
        return await self._async_set_setting({key: value})

    async def _async_set_setting(self, settings: dict[str, str | int]) -> None:
        """Validate the settings and then send the POST request."""
        for key, value in settings.items():
            _validate_setting(key, value)

        try:
            result = await self._async_settings_request(
                json=settings, method=CONST.HTTPMethod.POST
            )
        except SkybellException:
            _LOGGER.warning("Exception changing settings: %s", settings)
            result = None
            
        # Now we need to update the settings n the local device.
        if result is not None:
            old_settings = self._device_json.get(CONST.SETTINGS, {})
            UTILS.update(old_settings, result)

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
        return self._device_json.get(CONST.ACCOUNT_ID, "")

    @property
    def device_id(self) -> str:
        """Get the device id."""
        return self._device_id

    @property
    def name(self) -> str:
        """Get device name."""
        return self._device_json.get(CONST.NAME,"")

    @property
    def type(self) -> str:
        """Get device type."""
        return self._type

    @property
    def mac(self) -> str | None:
        """Get device mac address."""
        device_settings = self._device_json.get(CONST.DEVICE_SETTINGS, {})
        return device_settings.get(CONST.MAC_ADDRESS, "")

    @property
    def serial_no(self) -> str:
        """Get device serial number."""
        device_settings = self._device_json.get(CONST.DEVICE_SETTINGS, {})
        return device_settings.get(CONST.SERIAL_NUM, "")

    @property
    def firmware_ver(self) -> str:
        """Get device firmware version."""
        device_settings = self._device_json.get(CONST.DEVICE_SETTINGS, {})
        return device_settings.get(CONST.FIRMWARE_VERSION, "")

    @property
    def desc(self) -> str:
        """Get a short description of the device."""
        # Front Door (id: ) - skybell hd - status: up - wifi status: good
        string = f"{self.name} (id: {self.device_id}) - {self.type}"
        return f"{string} - status: {self.status} - wifi status: {self.wifi_link_quality}"

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
    def last_connected(self) -> datetime:
        """Get last connected timestamp."""
        tss = self._device_json.get(CONST.LAST_CONNECTED, "")
        try:
            ts = datetime.fromisoformat(tss)
        except ValueError:
            ts = ""
        return ts

    @property
    def last_disconnected(self) -> datetime:
        """Get last connected timestamp."""
        tss = self._device_json.get(CONST.LAST_DISCONNECTED, "")
        try:
            ts = datetime.fromisoformat(tss)
        except ValueError:
            ts = ""
        return ts
    
    @property
    def last_seen(self) -> datetime:
        """Get last checkin timestamp. If not availalbe return the last connected"""
        telemetry = self._device_json.get(CONST.DEVICE_TELEMETRY,{})
        tss = telemetry.get(CONST.DEVICE_LAST_SEEN, "")
        try:
            ts = datetime.fromisoformat(tss)
        except ValueError:
            ts = ""
        if not ts:
            ts = self.last_connected
        return ts

    @property
    def indoor_chime(self) -> bool:
        """Get if the devices indoor chime is enabled."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.INDOOR_CHIME)

    @property
    def digital_chime(self) -> bool:
        """Get if the devices indoor digital chime is enabled."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.INDOOR_DIGITAL_CHIME)
    @property
    def chime_file(self) -> str:
        """Get devices outdoor chime level."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.CHIME_FILE, CONST.CHIME_1WAV)

    @property
    def outdoor_chime(self) -> bool:
        """Get if the devices outdoor chime is enabled."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.OUTDOOR_CHIME)

    @property
    def outdoor_chime_volume(self) -> int:
        """Get devices outdoor chime volume."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return int(settings_json.get(CONST.OUTDOOR_CHIME_VOLUME, CONST.OUTDOOR_CHIME_LOW))

    @property
    def outdoor_chime_file(self) -> str:
        """Get devices outdoor chime level."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.OUTDOOR_CHIME_FILE, CONST.CHIME_1WAV)
    
    @property
    def speaker_volume(self) -> int:
        """Get devices livestream volume."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return int(settings_json.get(CONST.SPEAKER_VOLUME, CONST.SPEAKER_VOLUME_LOW))
    
    @property
    def led_control(self) -> str:
        """Get devices LED Control."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return settings_json.get(CONST.LED_CONTROL, "")

    @property
    def led_color(self) -> [int, int, int]:
        """Get devices LED color as red, green blue integers."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        hex_string = settings_json.get(CONST.LED_COLOR, "")
        
        if not hex_string:
            return [0,0,0]
        else:
            int_array = [int(hex_string[i:i+2], 16) for i in range(1, len(hex_string), 2)]
            return int_array
    
    @property
    def normal_led(self) -> bool:
        "Get the devices normal led enablement property."
        hex_string = ""
        if self.led_control == CONST.NORMAL_LED_CONTROL:
            settings_json = self._device_json.get(CONST.SETTINGS,{})
            hex_string = settings_json.get(CONST.LED_COLOR, "")
        return len(hex_string) > 0

    @property
    def image_quality(self) -> int:
        """Get devices livestream resolution."""
        settings_json = self._device_json.get(CONST.SETTINGS,{})
        return int(settings_json.get(CONST.IMAGE_QUALITY, CONST.IMAGE_QUALITY_LOW))

    @property
    def wifi_link_quality(self) -> str:
        """Get the wifi status."""
        telemetry = self._device_json.get(CONST.DEVICE_TELEMETRY,{})
        return telemetry.get(CONST.WIFI_LINK_QUALITY, "")

    @property
    def wifi_ssid(self) -> str:
        """Get the wifi ssid."""
        telemetry = self._device_json.get(CONST.DEVICE_TELEMETRY,{})
        ssid = telemetry.get(CONST.WIFI_SSID, "")
        if not ssid:
            settings_json = self._device_json.get(CONST.SETTINGS,{})
            ssid = settings_json.get(CONST.WIFI_ESSID, "")
        return ssid

def _validate_setting(  # pylint:disable=too-many-branches
    setting: str, value: str | int
) -> None:
    """Validate the public property setting and value."""
    if setting in CONST.BOOL_SETTINGS:
        if value not in CONST.BOOL_STRINGS:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.OUTDOOR_CHIME_VOLUME:
        if value not in CONST.OUTDOOR_CHIME_VALUES:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.SPEAKER_VOLUME:
        if value not in CONST.SPEAKER_VOLUME_VALUES:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.CHIME_FILE:
        if value not in CONST.CHIME_FILE_VALUES:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))

    if setting == CONST.OUTDOOR_CHIME_FILE:
        if value not in CONST.CHIME_FILE_VALUES:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))
    
    if setting == CONST.IMAGE_QUALITY:
        if value not in CONST.IMAGE_QUALITY_VALUES:
            raise SkybellException(ERROR.INVALID_SETTING_VALUE, (setting, value))
