"""Example usage of aioskybell."""
import asyncio

from aioskybell import Skybell
from aioskybell.helpers import const as CONST

async def async_example():
    """Example usage of aioskybell."""
    async with Skybell(username="user", password="password") as client:
        await client.async_update_cache({CONST.ACCESS_TOKEN: ""})
        devices = await client.async_initialize()
        for device in devices:
            await device.async_update()
            print(device.status)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(async_example())
except KeyboardInterrupt:
    pass
