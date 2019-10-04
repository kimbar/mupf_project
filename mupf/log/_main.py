import logging
import threading

# This must be before package imports or circular import occurs
log_mutex = threading.RLock()

from . import _address
from . import _manager
from . import _tracks
from . import settings

_logging_enabled = False
_filters_wo_handles_count = 0
_filters = {}
_default_all_on = True

def enable(file_name, * , file_mode = 'w', default_all_on=True):
    global _logging_enabled, _default_all_on
    _default_all_on = default_all_on
    logging.basicConfig(level=settings.logging_level)
    hand = logging.FileHandler(filename=file_name, mode=file_mode, encoding='utf-8')
    hand.setFormatter(logging.Formatter(settings.logging_format))
    logging.getLogger('').addHandler(hand)
    _tracks.set_style(_tracks._styles.get(settings.graph_style, 'default'))
    _logging_enabled = True
    _manager.refresh()

def add_filters(*args, **kwargs):
    for filter_ in args:
        _address.append_filter(filter_)
    for handle, filter_ in kwargs.items():
        _address.append_filter(filter_, handle)

def set_filters_state(**kwargs):
    global _filters
    for handle, state in kwargs.items():
        _filters[handle][0] = state[0]
    _manager.refresh()

def group_selector(event):
    return event.thread_name[0:settings.GROUP_NAME_WIDTH]
