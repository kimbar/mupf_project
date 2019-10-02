"""
Logging subsystem
"""

import logging

from ._decorator import loggable
from ._main import enable
from ._manager import LogManager
from ._writer import LogWriterStyle
