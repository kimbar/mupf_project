"""
Logging subsystem
"""

import logging
from ._decorator import loggable
from ._manager import LogManager
from ._writer import LogWriterStyle
from ._main import enable
