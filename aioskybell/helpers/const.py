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
ACTIVITY = "activity"
DEVICE_ID = "device_id"
LOCATION_LAT = "lat"
LOCATION_LON = "lon"
TYPE = "hardware"
LAST_CONNECTED = "last_connected"
LAST_DISCONNECTED = "last_disconnected"
UPDATED_AT = "updated_at"

# DEVUCE IMAGE SNAPSHOT
SNAPSHOT = "avatar"
PREVIEW_CREATED_AT = "date_time"
PREVIEW_IMAGE = "preview"

# DEVICE SETTINGS
DEVICE_SETTINGS = "device_settings"
DEVICE_NAME = "name"
DEVICE_OWNER = "account_id"
DEVICE_MAC = "MAC_address"
DEVICE_SERIAL_NO = "serial_number"
DEVICE_FIRMWARE_VERS = "firmware_version"
DEVICE_MOTION_DETECTION = "motion_detection"
DEVICE_BUTTON_DETECTION = "button_detection"

# ATTRIBUTES
ATTR_LAST_CHECK_IN = "last_check_in"
ATTR_WIFI_SSID = "wifi_ssid"
ATTR_WIFI_STATUS = "wifi_status"

ATTR_OWNER_STATS = [ATTR_LAST_CHECK_IN, ATTR_WIFI_SSID, ATTR_WIFI_STATUS]

#DEVICE TELEMETRY
DEVICE_TELEMETRY = "telemetry"
DEVICE_LAST_SEEN = "last_seen"
DEVICE_IP_ADDRESS = "ip_address"
WIFI_LINK_QUALITY = "link_quality"
WIFI_SIGNAL_LEVEL = "signal_level"
WIFI_SSID = "essid"


# DEVICE ACTIVITIES
ACTIVITY_ID = "activity_id"
ID = ACTIVITY_ID #Needed for HA integration
EVENT_TYPE = "event_type"
CREATED_AT = EVENT_TYPE  #Needed for HA integration
EVENT_TIME = "event_time"
EVENT_BUTTON = "device:sensor:button"
EVENT_MOTION = "device:sensor:motion"
EVENT_ON_DEMAND = "application:on-demand"
VIDEO_URL = "video_url"
DOWNLOAD_URL = "download_url"

STATE = "state"
STATE_READY = "ready"

VIDEO_STATE = "videoState"
VIDEO_STATE_READY = "download:ready"

# DEVICE SETTINGS
SETTINGS = "settings"
BRIGHTNESS = "brightness"
RGB_COLOR = "rgb_color"
LED_B = "green_b"
LED_G = "green_g"
LED_R = "green_r"
LED_COLORS = [LED_R, LED_G, LED_B]
MOTION_POLICY = "motion_policy"
MOTION_THRESHOLD = "motion_threshold"
OUTDOOR_CHIME = "chime_level"
VIDEO_PROFILE = "video_profile"
DO_NOT_DISTURB = "do_not_disturb"
DO_NOT_RING = "do_not_ring"

# SETTINGS Values
BOOL_STRINGS = ["True", "False"]

OUTDOOR_CHIME_OFF = 0
OUTDOOR_CHIME_LOW = 1
OUTDOOR_CHIME_MEDIUM = 2
OUTDOOR_CHIME_HIGH = 3
OUTDOOR_CHIME_VALUES = [
    OUTDOOR_CHIME_OFF,
    OUTDOOR_CHIME_LOW,
    OUTDOOR_CHIME_MEDIUM,
    OUTDOOR_CHIME_HIGH,
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

VIDEO_PROFILE_1080P = 0
VIDEO_PROFILE_720P_BETTER = 1
VIDEO_PROFILE_720P_GOOD = 2
VIDEO_PROFILE_480P = 3
VIDEO_PROFILE_VALUES = [
    VIDEO_PROFILE_1080P,
    VIDEO_PROFILE_720P_BETTER,
    VIDEO_PROFILE_720P_GOOD,
    VIDEO_PROFILE_480P,
]

LED_VALUES = [0, 255]

#Brightness values
BRIGHTNESS_VALUES = [0, 1000]
BRIGHTNESS_LOW = 0
BRIGHTNESS_MEDIUM = 1
BRIGHTNESS_HIGH = 2
#Brightness percent is between 3-1000 / 100
