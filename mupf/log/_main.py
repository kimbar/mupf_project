import logging
import threading

# This must be before package imports or circular import occurs
log_mutex = threading.RLock()

from . import _address
from . import _manager
from . import _tracks
from . import settings

_logging_enabled = False
_filters = []

def enable(file_name, * , file_mode = 'w', filters = ('+ ***',)):
    global _logging_enabled
    logging.basicConfig(level=settings.logging_level)
    hand = logging.FileHandler(filename=file_name, mode=file_mode, encoding='utf-8')
    hand.setFormatter(logging.Formatter(settings.logging_format))
    logging.getLogger('').addHandler(hand)
    _tracks.set_style(_tracks._styles.get(settings.graph_style, 'default'))
    for f in filters:
        _address.append_filter(f)
    _logging_enabled = True
    _manager.refresh()

def group_selector(event):
    return event.thread_name[0:4]
