"""
Logging subsystem
"""

import logging

from ._decorator import loggable, loggable_class
from ._main import enable, set_filters_state, add_filters
from ._manager import LogManager
from ._writer import LogWriterStyle
from . import settings
