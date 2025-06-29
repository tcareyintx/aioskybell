"""Example usage of aioskybell."""
import asyncio

from aioskybell import Skybell
from aioskybell.helpers import const as CONST

USER_NAME = "username"
PASSWORD = "password"

async def async_example():
    """Example usage of aioskybell."""
    # Sign on to Skybell API
    async with Skybell(username=USER_NAME, 
                       password=PASSWORD,
                       get_devices=True) as client:
        # Update the user and session cache
        await client.async_update_cache({CONST.ACCESS_TOKEN: ""})
        # Get the initial set of devices without events and activities
        devices = await client.async_initialize()
        for device in devices:
            # Update/refresh the activities and events
            await device.async_update()
            print("Device: %s, Status: %s" 
                    % (device.device_id, device.status))
                        
            # Example setting for LED color
            old_color = device.led_color
            new_color = [255,255,255]
            if old_color == new_color:
                new_color = [0,255,0]
                
            await device.async_set_setting(CONST.LED_COLOR, new_color)
            print("Device: %s, Old Color: %s New Color %s" 
                  % (device.device_id, old_color, device.led_color))

            # Refresh the device including activities and events
            await device.async_update(get_devices=True)


loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)
try:
    loop.run_until_complete(async_example())
except KeyboardInterrupt:
    pass
