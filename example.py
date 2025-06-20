"""Example usage of aioskybell."""
import asyncio

from aioskybell import Skybell
from aioskybell.helpers import const as CONST

USER_NAME = "username"
PASSWORD = "password"

async def async_example():
    """Example usage of aioskybell."""
    # Sign on to Skybell API
    async with Skybell(username=USER_NAME, password=PASSWORD) as client:
        # Update the user and session cache
        await client.async_update_cache({CONST.ACCESS_TOKEN: ""})
        # Get the initial set of devices without events and activities
        devices = await client.async_initialize()
        for device in devices:
            # Update/refresh the activities and events
            await device.async_update()
            print("Device: %s, Status: %s" 
                    % (device.device_id, device.status))
                        
            # Example setting - set_setting does not refresh the device
            old_brightness = device.led_intensity
            new_brightness = CONST.BRIGHTNESS_HIGH
            if old_brightness == CONST.BRIGHTNESS_HIGH:
                new_brightness = CONST.BRIGHTNESS_MEDIUM
                
            await device.async_set_setting(CONST.BRIGHTNESS, new_brightness)
            # Refresh the device including activities and events
            await device.async_update(get_devices=True)
            print("Device: %s, Old Brightness: %d New Brightness %d" 
                  % (device.device_id, old_brightness, device.led_intensity))


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(async_example())
except KeyboardInterrupt:
    pass
