"""AIOSkybell constants."""
from enum import Enum


class HTTPMethod(Enum):
    """HTTPMethod Enum."""

    DELETE = "DELETE"
    GET = "GET"
    PATCH = "PATCH"
    POST = "POST"


CACHE_PATH = "./skybell.pickle"

# URLS
BASE_API_DOMAIN = "https://api.skybell.network"
BASE_AUTH_DOMAIN = "https://api.skybell.network"

BASE_URL = "/api/v5"
BASE_API_URL = BASE_API_DOMAIN + BASE_URL

LOGIN_URL = BASE_AUTH_DOMAIN + BASE_URL + "/login/"
LOGOUT_URL = BASE_AUTH_DOMAIN + BASE_URL + "/logout/"

USER_URL = BASE_API_URL + "/user/"

DEVICES_URL = BASE_API_URL + "/devices/"
DEVICE_URL = DEVICES_URL + "$DEVID$/"

DEVICE_SNAPSHOT_URL = DEVICE_URL + "snapshot/"
DEVICE_SETTINGS_URL = DEVICE_URL + "settings/"

ACTIVITIES_URL = BASE_API_URL + "/activity"
ACTIVITY_URL = ACTIVITIES_URL + "/$ACTID$/"
ACTIVITY_VIDEO_URL = ACTIVITY_URL + "/video/"
DEVICE_ACTIVITIES_URL = ACTIVITIES_URL + "?device_id=$DEVID$"

# GENERAL
ACCESS_TOKEN = "AccessToken"
AUTHENTICATION_RESULT = "AuthenticationResult"

APP_ID = "app_id"
CLIENT_ID = "client_id"
DEVICES = "devices"
TOKEN = "token"
APP_VERSION = "1.238.1"
RESPONSE_DATA = "data"
RESPONSE_ROWS = "rows"

STATUS_UP = "Up"
STATUS_DOWN = "Down"

# User
USER_ID = "account_id"
FIRST_NAME = "fname"
LAST_NAME = "lname"

# DEVICE
DEVICE_ID = "device_id"
NAME = "name"
ACCOUNT_ID = "account_id"
CLIENT_ID = "client_id"
LOCATION_LAT = "lat"
LOCATION_LON = "lon"
LAST_CONNECTED = "last_connected"
LAST_DISCONNECTED = "last_disconnected"
LAST_EVENT = "last_event"
CREATED_AT = "created_at"
SHARED = "shared"
UPDATED_AT = "updated_at"
INVITE_TOKEN = "invite_token"
CERTIFICATE_ID = "certificate_id"

# DEVICE INFO
DEVICE_SETTINGS = "device_settings"
MAC_ADDRESS = "MAC_address"
MODEL_REV = "model_rev"
SERIAL_NUM = "serial_number"
HARDWARE_VERSION = "hardware_version"
FIRMWARE_VERSION = "firmware_version"
WIFI_ESSID = "ESSID"

#DEVICE TELEMETRY
DEVICE_TELEMETRY = "telemetry"
DEVICE_LAST_SEEN = "last_seen"
DEVICE_UPTIME = "uptime"
DEVICE_BOOT_TIME = "boot_time"
DEVICE_IP_ADDRESS = "ip_address"
DEVICE_IP_SUBNET = "ip_subnet"
DEVICE_PUBLIC_IP = "ip_address_public"

WIFI_LINK_QUALITY = "link_quality"
WIFI_SIGNAL_LEVEL = "signal_level"
WIFI_NETWORK_SIGNAL = "network_frequency"
WIFI_NOISE = "wifi_noise"
WIFI_SSID = "essid"

# DEVICE ACTIVITIES
ACTIVITY = "activity"
ACTIVITY_ID = "activity_id"
EVENT_TYPE = "event_type"
EVENT_TIME = "event_time"
VIDEO_URL = "video_url"
VIDEO_READY = "video_ready"
DOWNLOAD_URL = "download_url"

# DEVUCE IMAGE SNAPSHOT
SNAPSHOT = "avatar"
PREVIEW_CREATED_AT = "date_time"
PREVIEW_IMAGE = "preview"

# DEVICE BASIC MOTION

# DEVICE SETTINGS
SETTINGS = "settings"
# NORMAL LED SETTINGS
LED_CONTROL = "led_control"
LED_COLOR = "led_color"

# AUDIO SETTUBGS
INDOOR_CHIME = "indoor_chime"
INDOOR_DIGITAL_CHIME = "digital_chime"
CHIME_FILE = "chime_file"
OUTDOOR_CHIME = "outdoor_chime"
OUTDOOR_CHIME_VOLUME = "outdoor_chime_volume"
OUTDOOR_CHIME_FILE = "outdoor_chime_file"
SPEAKER_VOLUME = "speaker_volume"

# MOTION SETTiNGS
MOTION_DETECTION = "motion_detection"
DEBUG_MOTION_DETECTiON = "debug_motion_detection"
MOTION_SENSITIVITY = "motion_sensitivity"
MOTION_HMBD_SENSITIVITY = "hmbd_sensistivity" # Human Motion Body Detection
MOTION_FD_SENSITIVITY = "fd_sensitivity" # Face Detection
MOTION_FR_SENSITIVITY = "fr_sensitivity" # Face Recognition

#IMAGE SETTINGS
IMAGE_QUALITY = "image_quality"
VIDEO_ROTATION = "video_rotation"

# SETTINGS Values
BOOL_SETTINGS = [
    INDOOR_CHIME,
    INDOOR_DIGITAL_CHIME,
    OUTDOOR_CHIME,
    MOTION_DETECTION,
]
BOOL_STRINGS = ["True", "False"]

#OUTDOOR CHIME FOR DOORBELLS
OUTDOOR_CHIME_LOW = 0
OUTDOOR_CHIME_MEDIUM = 1
OUTDOOR_CHIME_HIGH = 2

OUTDOOR_CHIME_VALUES = [
    OUTDOOR_CHIME_LOW,
    OUTDOOR_CHIME_MEDIUM,
    OUTDOOR_CHIME_HIGH,
]

#SPEAKER VOLUME
SPEAKER_VOLUME_LOW = 0
SPEAKER_VOLUME_MEDIUM = 1
SPEAKER_VOLUME_HIGH = 2

SPEAKER_VOLUME_VALUES = [
    SPEAKER_VOLUME_LOW,
    SPEAKER_VOLUME_MEDIUM,
    SPEAKER_VOLUME_HIGH,
]

LED_VALUES = [0, 255]
NORMAL_LED_CONTROL = "Normal"
NORMAL_LED = "normal_led"
DEFAULT_NORMAL_LED_COLOR = "x00ff00" # Green

IMAGE_QUALITY_LOW = 0
IMAGE_QUALITY_MEDIUM = 1
IMAGE_QUALITY_HIGH = 2
IMAGE_QUALITY_HIGHEST = 3
IMAGE_QUALITY_VALUES = [
    IMAGE_QUALITY_LOW,
    IMAGE_QUALITY_MEDIUM,
    IMAGE_QUALITY_HIGH,
    IMAGE_QUALITY_HIGHEST,
]

MOTION_POLICY_OFF = "disabled"
MOTION_POLICY_ON = "call"
MOTION_POLICY_VALUES = [MOTION_POLICY_OFF, MOTION_POLICY_ON]

MOTION_THRESHOLD_LOW = 100
MOTION_THRESHOLD_MEDIUM = 50
MOTION_THRESHOLD_HIGH = 32
MOTION_THRESHOLD_VALUES = [
    MOTION_THRESHOLD_LOW,
    MOTION_THRESHOLD_MEDIUM,
    MOTION_THRESHOLD_HIGH,
]


#UNUSED - TODO REMOVE
CREATED_AT = EVENT_TYPE  #Needed for HA integration
ID = ACTIVITY_ID #Needed for HA integration

EVENT_BUTTON = "device:sensor:button"
EVENT_MOTION = "device:sensor:motion"
EVENT_ON_DEMAND = "application:on-demand"
# ATTRIBUTES
ATTR_LAST_CHECK_IN = "last_check_in"
ATTR_WIFI_SSID = "wifi_ssid"
ATTR_WIFI_STATUS = "wifi_status"

ATTR_OWNER_STATS = [ATTR_LAST_CHECK_IN, ATTR_WIFI_SSID, ATTR_WIFI_STATUS]

STATE = "state"
STATE_READY = "ready"
