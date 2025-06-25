"""Models for Skybell."""
from __future__ import annotations

class MotionZoneData(dict):
    """Class for Motion zone object permitted for the device. 
       See /api/v5/devices/DEVICE_ID/settings"""

    ignore: bool | None
    sensitivity: int | None

class MotionZoneConfigData(dict):
    """Class for Motion zone settings (motion_zone_config) 
       permitted for the device. 
       See /api/v5/devices/DEVICE_ID/settings"""

    x: int | None
    y: int | None
    threshold: str | None
    zones: list[list[list[MotionZoneData]]]

# ToDo Need to add the motion zone
class SettingsData(dict):
    """Class for update settings permitted for the device.
       See /api/v5/devices/DEVICE_ID/settings"""

    device_name: str | None
    time_zone: str | None
    led_color: str | None
    brightness: int | None
    indoor_chime: bool | None
    digital_chime: bool | None
    outdoor_chime: bool | None
    outdoor_chime_volume: int | None
    motion_detection: bool | None
    debug_motion_detect: bool | None
    motion_sensitivity: int | None
    hmbd_sensitivity: int | None
    fd_sensitivity: int | None
    fr_sensitivity: int | None
    image_quality: int | None
    video_rotation: int | None
    speaker_volume: str | None
    chime_file: str | None
    motion_zone_config: MotionZoneConfigData | None


class DeviceSettingsData(dict):
    """Class for device_settings in a retrieved device.
       See /api/v5/devices/DEVICE_ID"""
    
    essid: str
    ota_type: str
    model_rev: str
    mac_address: str
    ota_version: str
    ota_signature: str
    serial_number: str
    firmware_patch: str
    firmware_version: str
    firmare_major_release: str
    
class TelemetryData(dict):
    """Class for telemetry in a retrieved device.
       See /api/v5/devices/DEVICE_ID"""
    
    uptime: str
    boot_time: str
    timestamp: str
    wifi_noise: str
    link_quality: str
    signal_level: str
    wifi_bit_rate: str
    network_frequency: str
    
class SnapshotData(dict):
    """Class for the device snapshot (avatar) 
       in a retrieved device. See /api/v5/devices/DEVICE_ID"""

    date_time: str
    preview: str

class DeviceData(dict):
    """Class for device.
       See /api/v5/devices/DEVICE_ID"""

    device_id: str
    client_id: str
    account_id: str
    serial: str
    certificate_id: str
    hardware: str
    firmware: str
    invite_token: str
    last_event: str
    last_connected: str
    last_disconnected: str
    lat: str
    lon: str
    name: str
    manufactured: str
    created_at: str
    updated_at: str
    device_settings: DeviceSettingsData
    telemetry: TelemetryData
    settings: SettingsData

class ActivityData(dict):
    """Class for an activity (event).
       See /api/v5/activities"""
    
    event_time: int
    account_id: str
    device_id: str
    device_name: str
    activity_id: str
    event_type: str
    date: str
    video_url: str
    video_ready: bool
    image: str | None
    edge_tags: list
    ai_ppe: str | None
    created_at: str
    video_size: int
    video_ready_time: str
    
    
ActivityType = dict[str, ActivityData]
DeviceType = dict[str, dict[str, ActivityType]]
DevicesDict = dict[str, DeviceType]
