"""Import pure service modules directly so tests never pull in the app/DB layer."""
from __future__ import annotations

import os
import sys

_SERVICES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services")
if _SERVICES_DIR not in sys.path:
    sys.path.insert(0, _SERVICES_DIR)
