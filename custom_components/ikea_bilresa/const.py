"""Constants for the IKEA BILRESA (smooth scroll) integration."""

from __future__ import annotations

DOMAIN = "ikea_bilresa"

# Default Matter Server (add-on) WebSocket URL. Overridden by the URL taken
# from the core `matter` config entry when one is available.
DEFAULT_MATTER_URL = "ws://core-matter-server:5580/ws"

CONF_URL = "url"

# --- Matter cluster / attribute ids -------------------------------------
CLUSTER_SWITCH = 0x003B  # 59  Switch cluster
CLUSTER_DESCRIPTOR = 0x001D  # 29  Descriptor cluster
CLUSTER_BASIC_INFO = 0x0028  # 40  Basic Information cluster

ATTR_DESCRIPTOR_PARTS_LIST = 3  # Descriptor.PartsList
ATTR_DESCRIPTOR_TAGLIST = 4  # Descriptor.TagList
ATTR_BASIC_VENDOR_NAME = 1
ATTR_BASIC_VENDOR_ID = 2
ATTR_BASIC_PRODUCT_NAME = 3

IKEA_VENDOR_ID = 4476  # 0x117C
BILRESA_PRODUCT_MATCH = "bilresa"

# --- Semantic tag namespaces (Matter "Common" namespaces) ---------------
NS_SWITCHES = 0x43  # 67  Common Switches namespace

# Switches namespace tags
SWTAG_ON = 0x00
SWTAG_OFF = 0x01
SWTAG_TOGGLE = 0x02
SWTAG_UP = 0x03
SWTAG_DOWN = 0x04
SWTAG_NEXT = 0x05
SWTAG_PREVIOUS = 0x06
SWTAG_ENTER_OK = 0x07
SWTAG_CUSTOM = 0x08

# TagList entry keys (as delivered by the Matter Server, TLV field numbers)
TAG_KEY_NAMESPACE = "1"  # NamespaceID
TAG_KEY_TAG = "2"  # Tag
TAG_KEY_LABEL = "3"  # Label (optional, human string)

# --- Switch cluster events (cluster 0x003B) -----------------------------
EVT_SWITCH_LATCHED = 0x00
EVT_INITIAL_PRESS = 0x01
EVT_LONG_PRESS = 0x02
EVT_SHORT_RELEASE = 0x03
EVT_LONG_RELEASE = 0x04
EVT_MULTI_PRESS_ONGOING = 0x05
EVT_MULTI_PRESS_COMPLETE = 0x06

SWITCH_EVENT_NAMES = {
    EVT_SWITCH_LATCHED: "switch_latched",
    EVT_INITIAL_PRESS: "initial_press",
    EVT_LONG_PRESS: "long_press",
    EVT_SHORT_RELEASE: "short_release",
    EVT_LONG_RELEASE: "long_release",
    EVT_MULTI_PRESS_ONGOING: "multi_press_ongoing",
    EVT_MULTI_PRESS_COMPLETE: "multi_press_complete",
}

# Roles a switch endpoint can play on the wheel
ROLE_SCROLL_UP = "scroll_up"
ROLE_SCROLL_DOWN = "scroll_down"
ROLE_BUTTON = "button"

# HA event-bus event fired for every decoded wheel action
EVENT_BILRESA = "ikea_bilresa_event"

# Data keys inside a Matter switch event payload (camelCase, as delivered by
# the Matter Server). To be re-confirmed against live device logs in phase 1.
DATA_NEW_POSITION = "newPosition"
DATA_PREVIOUS_POSITION = "previousPosition"
DATA_CURRENT_COUNT = "currentNumberOfPressesCounted"
DATA_TOTAL_COUNT = "totalNumberOfPressesCounted"

# --- Clean, high-level actions (emitted by the gesture engine) ----------
ACTION_ROTATE = "rotate"
ACTION_PRESS = "press"
ACTION_HOLD = "hold"
ACTION_RELEASE = "release"

DIRECTION_UP = "up"
DIRECTION_DOWN = "down"

# --- event entity event_types (one entity per wheel channel) ------------
ET_ROTATE_UP = "rotate_up"
ET_ROTATE_DOWN = "rotate_down"
ET_PRESS = "press"
ET_DOUBLE_PRESS = "double_press"
ET_TRIPLE_PRESS = "triple_press"
ET_HOLD = "hold"
ET_RELEASE = "release"

WHEEL_EVENT_TYPES = [
    ET_ROTATE_UP,
    ET_ROTATE_DOWN,
    ET_PRESS,
    ET_DOUBLE_PRESS,
    ET_TRIPLE_PRESS,
    ET_HOLD,
    ET_RELEASE,
]

PRESS_EVENT_TYPES = {1: ET_PRESS, 2: ET_DOUBLE_PRESS, 3: ET_TRIPLE_PRESS}

# --- config subentries (GUI light bindings) -----------------------------
SUBENTRY_BINDING = "binding"

CONF_NODE_ID = "node_id"
CONF_CHANNEL = "channel"
CONF_TARGET = "target"
CONF_MODE = "mode"
CONF_STEP = "step"
CONF_ACCELERATION = "acceleration"
CONF_MIN_BRIGHTNESS = "min_brightness"
CONF_MAX_BRIGHTNESS = "max_brightness"
CONF_TRANSITION = "transition"
CONF_CLICK_ACTION = "click_action"
CONF_BUTTON_RESPONSE = "button_response"
CONF_CLICK_TARGET = "click_target"
CONF_DOUBLE_TARGET = "double_press_target"
CONF_TRIPLE_TARGET = "triple_press_target"
CONF_HOLD_TARGET = "hold_target"
CONF_HOLD_ACTION = "hold_action"
CONF_SCENES = "scenes"

# Flow-only convenience fields used when creating a binding.
CONF_BINDING_PROFILE = "binding_profile"
CONF_COPY_FROM = "copy_from"
BINDING_PROFILE_CUSTOM = "custom"
BINDING_PROFILE_LIGHT = "light"
BINDING_PROFILE_MEDIA = "media"
BINDING_PROFILE_COVER = "cover"
BINDING_PROFILE_CLIMATE = "climate"
BINDING_PROFILE_SCENES = "scenes"
BINDING_PROFILES = [
    BINDING_PROFILE_CUSTOM,
    BINDING_PROFILE_LIGHT,
    BINDING_PROFILE_MEDIA,
    BINDING_PROFILE_COVER,
    BINDING_PROFILE_CLIMATE,
    BINDING_PROFILE_SCENES,
]

# What holding the button does.
HOLD_TOGGLE = "toggle"  # toggle the hold target entity (default)
HOLD_RAMP = "ramp"  # continuously ramp the scroll target while held
HOLD_NONE = "none"
HOLD_ACTIONS = [HOLD_TOGGLE, HOLD_RAMP, HOLD_NONE]
DEFAULT_HOLD_ACTION = HOLD_TOGGLE

DEFAULT_STEP = 3
DEFAULT_ACCELERATION = 0
DEFAULT_MIN_BRIGHTNESS = 1
DEFAULT_MAX_BRIGHTNESS = 100
DEFAULT_TRANSITION = 1.0
DEFAULT_CLICK_ACTION = "toggle"

# When the configured single-press action runs.  Missing values intentionally
# keep the historic completion-aware behavior for existing stored bindings.
BUTTON_RESPONSE_FAST = "fast"
BUTTON_RESPONSE_MULTI_PRESS = "multi_press"
BUTTON_RESPONSES = [BUTTON_RESPONSE_FAST, BUTTON_RESPONSE_MULTI_PRESS]
DEFAULT_BUTTON_RESPONSE = BUTTON_RESPONSE_MULTI_PRESS

# Scroll modes: what a rotation changes on the target entity.
MODE_BRIGHTNESS = "brightness"
MODE_COLOR_TEMP = "color_temp"
MODE_COLOR = "color"
MODE_VOLUME = "volume"
MODE_COVER = "cover_position"
MODE_TEMPERATURE = "temperature"
MODE_FAN = "fan_speed"
MODE_NUMBER = "number"
MODES = [
    MODE_BRIGHTNESS,
    MODE_COLOR_TEMP,
    MODE_COLOR,
    MODE_VOLUME,
    MODE_COVER,
    MODE_TEMPERATURE,
    MODE_FAN,
    MODE_NUMBER,
]
DEFAULT_MODE = MODE_BRIGHTNESS

MODE_TARGET_DOMAINS = {
    MODE_BRIGHTNESS: frozenset({"light"}),
    MODE_COLOR_TEMP: frozenset({"light"}),
    MODE_COLOR: frozenset({"light"}),
    MODE_VOLUME: frozenset({"media_player"}),
    MODE_COVER: frozenset({"cover"}),
    MODE_TEMPERATURE: frozenset({"climate"}),
    MODE_FAN: frozenset({"fan"}),
    MODE_NUMBER: frozenset({"number", "input_number"}),
}


def mode_supports_target(mode: str, entity_id: str) -> bool:
    """Return whether a scroll mode supports the target entity domain."""
    domain, separator, _object_id = entity_id.partition(".")
    return bool(separator and domain in MODE_TARGET_DOMAINS.get(mode, frozenset()))


# Entity domains a binding can target (its scroll control adapts to the mode).
TARGET_DOMAINS = [
    "light",
    "media_player",
    "cover",
    "climate",
    "fan",
    "number",
    "input_number",
]

CLICK_TOGGLE = "toggle"
CLICK_ON = "on"
CLICK_OFF = "off"
CLICK_NONE = "none"
CLICK_ACTIONS = [CLICK_TOGGLE, CLICK_ON, CLICK_OFF, CLICK_NONE]

# Sensible fallback white-temperature range (Kelvin) if a light doesn't report it.
FALLBACK_MIN_KELVIN = 2000
FALLBACK_MAX_KELVIN = 6500

# --- dispatcher signals -------------------------------------------------
SIGNAL_WHEELS_UPDATED = f"{DOMAIN}_wheels_updated"
SIGNAL_CONNECTION = f"{DOMAIN}_connection"

# --- repair issues ------------------------------------------------------
ISSUE_CANNOT_CONNECT = "cannot_connect"
# Grace period before a lost connection is surfaced as a repair issue.
DISCONNECT_GRACE_SECONDS = 60


def signal_channel(node_id: int, channel: int | None) -> str:
    """Per wheel-channel dispatcher signal carrying decoded WheelActions."""
    return f"{DOMAIN}_action_{node_id}_{channel}"


def signal_raw_button(node_id: int, channel: int | None) -> str:
    """Internal per-channel signal carrying raw button event names."""
    return f"{DOMAIN}_raw_button_{node_id}_{channel}"
