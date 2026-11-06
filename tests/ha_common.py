"""Home Assistant's test helpers, wherever the installed version keeps them.

Up to 2026.10 they ship as ``pytest_homeassistant_custom_component``; from
2026.11 Home Assistant publishes them itself as ``pytest_homeassistant``. The
tests import from here so one file knows about the move. This module *is* the
helper module (a star import would only carry what its ``__all__`` lists).
"""

import importlib
import sys

try:
    _helpers = importlib.import_module("pytest_homeassistant.common")
except ImportError:  # Home Assistant 2026.10 and older
    _helpers = importlib.import_module("pytest_homeassistant_custom_component.common")

sys.modules[__name__] = _helpers
