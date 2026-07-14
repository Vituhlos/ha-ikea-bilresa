"""Constants for the IKEA BILRESA (smooth scroll) integration."""

from __future__ import annotations

DOMAIN = "ikea_bilresa"

# Default Matter Server (add-on) WebSocket URL. Overridden by the URL taken
# from the core `matter` config entry when one is available.
DEFAULT_MATTER_URL = "ws://core-matter-server:5580/ws"

CONF_URL = "url"

# --- Matter cluster / attribute ids -------------------------------------
CLUSTER_SWITCH = 0x003B          # 59  Switch cluster
CLUSTER_DESCRIPTOR = 0x001D      # 29  Descriptor cluster
CLUSTER_BASIC_INFO = 0x0028      # 40  Basic Information cluster

ATTR_DESCRIPTOR_PARTS_LIST = 3   # Descriptor.PartsList
ATTR_DESCRIPTOR_TAGLIST = 4      # Descriptor.TagList
ATTR_BASIC_VENDOR_NAME = 1
ATTR_BASIC_VENDOR_ID = 2
ATTR_BASIC_PRODUCT_NAME = 3

IKEA_VENDOR_ID = 4476            # 0x117C
BILRESA_PRODUCT_MATCH = "bilresa"

# --- Semantic tag namespaces (Matter "Common" namespaces) ---------------
NS_SWITCHES = 0x43               # 67  Common Switches namespace

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
TAG_KEY_NAMESPACE = "1"          # NamespaceID
TAG_KEY_TAG = "2"                # Tag
TAG_KEY_LABEL = "3"              # Label (optional, human string)

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
