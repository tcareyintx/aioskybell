"""An asynchronous client for Skybell API.

Async spinoff of: https://github.com/MisterWil/skybellpy

Published under the MIT license - See LICENSE file for more details.

"Skybell" is a trademark owned by SkyBell Technologies, Inc, see
www.skybell.com for more information. I am in no way affiliated with Skybell.
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from asyncio.exceptions import TimeoutError as Timeout
from typing import Any, Collection

from aiohttp.client import ClientSession, ClientTimeout
from aiohttp.client_exceptions import ClientConnectorError, ClientError

from . import utils as UTILS
from .device import SkybellDevice
from .exceptions import SkybellAuthenticationException, SkybellRequestException
from .exceptions import SkybellException, SkybellUnknownResourceException
from .helpers import const as CONST
from .helpers import errors as ERROR

_LOGGER = logging.getLogger(__name__)


class Skybell:  # pylint:disable=too-many-instance-attributes
    """Main Skybell class."""

    _close_session = False

    def __init__(  # pylint:disable=too-many-arguments
        self,
        username: str | None = None,
        password: str | None = None,
        auto_login: bool = False,
        get_devices: bool = True,
        cache_path: str = CONST.CACHE_PATH,
        disable_cache: bool = False,
        login_sleep: bool = True,
        session: ClientSession | None = None,
    ) -> None:
        """Initialize Skybell object."""
        self._auto_login = auto_login
        self._cache_path = cache_path
        self._devices: dict[str, SkybellDevice] = {}
        self._disable_cache = disable_cache
        self._get_devices = get_devices
        self._password = password
        if username is not None and self._cache_path == CONST.CACHE_PATH:
            self._cache_path = f"skybell_{username.replace('.', '')}.pickle"
        self._username = username
        if session is None:
            session = ClientSession()
            self._close_session = True
        self._session = session
        self._login_sleep = login_sleep
        self._user: dict[str, str] = {}

        # Create a new cache template
        self._cache: dict[str, str] = {
            CONST.AUTHENTICATION_RESULT: {},
        }

    async def __aenter__(self) -> Skybell:
        """Async enter."""
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        """Async exit."""
        if self._session and self._close_session:
            await self._session.close()

    async def async_initialize(self) -> list[SkybellDevice]:
        """Initialize."""
        if not self._disable_cache:
            await self._async_load_cache()

        # Login option on initialization, otherwise wait until
        # A request is made
        if (
            self._username is not None
            and self._password is not None
            and self._auto_login
        ):
            await self.async_login()

        # Obtain the user data -  which will login
        self._user = None
        try:
            self._user = await self.async_send_request(CONST.USER_URL)
        except SkybellException as ex:
            raise ex
        except Exception:
            _LOGGER.error("Unable to send user request: %s", self._username)

        if self._user is not None and self._get_devices:
            # Obtain the devices for the user
            try:
                return await self.async_get_devices()
            except Exception:
                _LOGGER.error("Unable to get devices for user: %s",
                              self._username)
                return {}
        else:
            return {}

    async def async_login(
        self, username: str | None = None, password: str | None = None
    ) -> bool:
        """Execute Skybell login."""
        if username is not None:
            self._username = username
        if password is not None:
            self._password = password

        if self._username is None or self._password is None:
            raise SkybellAuthenticationException(
                self, f"{ERROR.USERNAME}: {ERROR.PASSWORD}"
            )

        # Clear any cached login data
        await self.async_update_cache({CONST.AUTHENTICATION_RESULT: {}})

        login_data: dict[str, str | int] = {
            "username": self._username,
            "password": self._password,
        }

        response = None
        try:
            response = await self.async_send_request(
                url=CONST.LOGIN_URL,
                json=login_data,
                method=CONST.HTTPMethod.POST,
                retry=False,
            )
        except SkybellAuthenticationException as ex:
            raise ex
        except SkybellException as ex:
            raise ex
        except Exception:
            _LOGGER.error("Unable to send user login: %s", self._username)
            return False

        _LOGGER.debug("Login Response: %s", response)
        # Store the Authorization result
        auth_result = response[CONST.AUTHENTICATION_RESULT]
        # Add an expiration date
        expires_in = auth_result[CONST.TOKEN_EXPIRATION]
        expiration = UTILS.calculate_expiration(
            expires_in=expires_in,
            slack=CONST.EXPIRATION_SLACK,
            refresh_cycle=CONST.REFRESH_CYCLE,
        )
        auth_result[CONST.EXPIRATION_DATE] = expiration
        await self.async_update_cache(
            {CONST.AUTHENTICATION_RESULT: auth_result})

        if self._login_sleep:
            _LOGGER.info("Login successful, waiting 5 seconds...")
            await asyncio.sleep(5)
        else:
            _LOGGER.info("Login successful")

        return True

    async def async_logout(self) -> bool:
        """Explicit Skybell logout."""
        if len(self.cache(CONST.AUTHENTICATION_RESULT)) > 0:
            # No explicit logout call as it doesn't seem to matter
            # if a logout happens without registering the app which
            # we aren't currently doing.
            if self._session and self._close_session:
                await self._session.close()
            self._devices = {}

        await self.async_update_cache({CONST.AUTHENTICATION_RESULT: {}})

        return True

    async def async_refresh_session(self) -> bool:
        """Execute Skybell refresh."""

        auth_result = self.cache(CONST.AUTHENTICATION_RESULT)
        if auth_result:
            refresh_token = auth_result.get(CONST.REFRESH_TOKEN, "")
        else:
            refresh_token = ""

        if not self._session or not refresh_token:
            raise SkybellAuthenticationException(self,
                                                 "No session established")

        body_data: dict[str, str | int] = {
            CONST.REFRESH_TOKEN_BODY: refresh_token,
        }

        response = None
        try:
            response = await self.async_send_request(
                url=CONST.REFRESH_TOKEN_URL,
                json=body_data,
                method=CONST.HTTPMethod.PUT,
                retry=False,
            )
        except Exception:
            _LOGGER.debug("No Token Refresh Response returned.")
            return False

        _LOGGER.debug("Token Refresh Response: %s", response)

        # Add an expiration date
        expires_in = response[CONST.TOKEN_EXPIRATION]
        expiration = UTILS.calculate_expiration(
            expires_in=expires_in,
            slack=CONST.EXPIRATION_SLACK,
            refresh_cycle=CONST.REFRESH_CYCLE,
        )
        response[CONST.EXPIRATION_DATE] = expiration
        # Update the cache entities
        UTILS.update(auth_result, response)
        await self.async_update_cache(
            {CONST.AUTHENTICATION_RESULT: auth_result})
        _LOGGER.debug("Refresh successful")
        return True

    async def async_get_devices(self, refresh: bool = False
                                ) -> list[SkybellDevice]:
        """Get all devices from Skybell."""
        if refresh or len(self._devices) == 0:
            _LOGGER.info("Updating all devices...")
            response = await self.async_send_request(CONST.DEVICES_URL)
            _LOGGER.debug("Get Devices Response: %s", response)
            response_rows = response[CONST.RESPONSE_ROWS]
            for device_json in response_rows:
                device = self._devices.get(device_json[CONST.DEVICE_ID])

                # No existing device, create a new one
                if device:
                    await device.async_update(
                        {device_json[CONST.DEVICE_ID]: device_json}
                    )
                else:
                    device = SkybellDevice(device_json, self)
                    self._devices[device.device_id] = device

        return list(self._devices.values())

    async def async_get_device(
        self, device_id: str, refresh: bool = False
    ) -> SkybellDevice:
        """Get a single device."""
        if len(self._devices) == 0:
            try:
                await self.async_get_devices()
                refresh = False
            except Exception as exc:
                raise SkybellException(
                    self, "Unable to retrieve devices")from exc

        device = self._devices.get(device_id)

        if not device:
            raise SkybellException(self, "Device not found")
        if refresh:
            await device.async_update()

        return device

    @property
    def user_id(self) -> str | None:
        """Return logged in user id."""
        return self._user.get(CONST.USER_ID, None)

    @property
    def user_first_name(self) -> str | None:
        """Return logged in user first name."""
        return self._user.get(CONST.FIRST_NAME, None)

    @property
    def user_last_name(self) -> str | None:
        """Return logged in user last name."""
        return self._user.get(CONST.LAST_NAME, None)

    @property
    def session_refresh_period(self) -> int:
        """Return period, in seconds, that the session will last
        without a refresh of the login.
        """
        auth_result = self.cache(CONST.AUTHENTICATION_RESULT)
        if auth_result:
            period = auth_result.get(CONST.TOKEN_EXPIRATION, 0)
        else:
            period = 0
        return period

    @property
    def session_refresh_timestamp(self) -> datetime | None:
        """Return expiration datetime that the session will last
        without a refresh of the login.
        """
        expires = None
        auth_result = self.cache(CONST.AUTHENTICATION_RESULT)
        if auth_result:
            expires = auth_result.get(CONST.EXPIRATION_DATE, None)

        return expires

    async def async_send_request(  # pylint:disable=too-many-arguments
        self,
        url: str,
        headers: dict[str, str] | None = None,
        method: CONST.HTTPMethod = CONST.HTTPMethod.GET,
        retry: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Send requests to Skybell."""
        if (len(self.cache(CONST.AUTHENTICATION_RESULT)) == 0 and
                url != CONST.LOGIN_URL):
            response = await self.async_login()
            if response is False:
                _LOGGER.exception("Failed login unable to send request: %s",
                                  url)
                raise SkybellAuthenticationException(
                    f"Failed login unable to send request: {url}"
                )

        headers = headers if headers else {}
        if (CONST.BASE_AUTH_DOMAIN in url or CONST.BASE_API_DOMAIN in url):
            auth_result = self.cache(CONST.AUTHENTICATION_RESULT)
            token = auth_result.get(CONST.ID_TOKEN, "")
            token_type = auth_result.get(CONST.TOKEN_TYPE, "")
            if token and token_type:
                headers["Authorization"] = f"Bearer {token}"
            headers["content-type"] = "application/json"
            headers["accept"] = "*/*"
            headers["x-skybell-app"] = CONST.APP_VERSION

        _LOGGER.debug("HTTP %s %s Request with headers: %s",
                      method, url, headers)

        try:
            response = await self._session.request(
                method.value,
                url,
                headers=headers,
                timeout=ClientTimeout(30),
                **kwargs,
            )
            if response.status == 401 or (
                response.status == 403 and CONST.LOGIN_URL == url
            ):
                await self.async_update_cache(
                    {CONST.AUTHENTICATION_RESULT: {}})
                raise SkybellAuthenticationException(await response.text())
            elif response.status in (403, 404):
                # 403/404 for expired request/device key no
                # longer present in S3
                _LOGGER.exception(await response.text())
                raise SkybellUnknownResourceException(await response.text())
            elif response.status == 400:
                # Bad request problem that cant be fixed by user or logging in
                _LOGGER.exception(await response.text())
                raise SkybellRequestException(await response.text())
            response.raise_for_status()
        except ClientError as ex:
            if retry:
                await self.async_login()

                return await self.async_send_request(
                    url, headers=headers, method=method, retry=False, **kwargs
                )
            raise SkybellException from ex
        if response.content_type == "application/json":
            local_response = await response.json()
        else:
            local_response = await response.read()
        # Now we have a local response which could be
        # a json dictionary or byte stream
        if isinstance(local_response, dict):
            return local_response.get(CONST.RESPONSE_DATA, {})
        else:
            return local_response

    def cache(self, key: str) -> str | Collection[str]:
        """Get a cached value."""
        return self._cache.get(key, "")

    async def async_update_cache(self, data: dict[str, str]) -> None:
        """Update a cached value."""
        UTILS.update(self._cache, data)
        await self._async_save_cache()

    async def _async_load_cache(self) -> None:
        """Load existing cache and merge for updating if required."""
        if not self._disable_cache:
            if os.path.exists(self._cache_path):
                _LOGGER.debug("Cache found at: %s", self._cache_path)
                if os.path.getsize(self._cache_path) > 0:
                    loaded_cache = await UTILS.async_load_cache(
                        self._cache_path)
                    UTILS.update(self._cache, loaded_cache)
                else:
                    _LOGGER.debug("Cache file is empty.  Removing it.")
                    os.remove(self._cache_path)

        await self._async_save_cache()

    async def _async_save_cache(self) -> None:
        """Trigger a cache save."""
        if not self._disable_cache:
            await UTILS.async_save_cache(self._cache, self._cache_path)

    async def async_delete_cache(self) -> None:
        """Remove the cache if required."""
        if os.path.exists(self._cache_path):
            _LOGGER.debug("Removing cache found at: %s", self._cache_path)
            os.remove(self._cache_path)
            self._cache_path = CONST.CACHE_PATH

    async def async_test_ports(
        self, host: str,
        ports: list[int] | None = None
    ) -> bool:
        """Test if ports are open. Only use this for discovery."""
        result = False
        for port in ports or [6881, 6969]:
            try:
                await self._session.get(
                    f"http://{host}:{port}",
                    timeout=ClientTimeout(10),
                )
            except ClientConnectorError as ex:
                if ex.errno == 61:
                    result = True
            except Timeout:
                return False
        return result
