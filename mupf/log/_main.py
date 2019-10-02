import logging
import threading

# This must be before package imports or circular import occurs
MIN_COLUMN_WIDTH = 90    # minimum width of the column with names of functions
TAB_WIDTH = 20           # if the width is not enough, this much is added in one go
THREAD_TAB_WIDTH = 10    # the spacing for another thread graph column
GROUP_WIDTH = 10
log_mutex = threading.RLock()

from . import _address as address
from . import _manager as manager
from . import _tracks as tracks

_logging_enabled = False
_filters = []

def enable(filename, fmt='[%(name)s] %(message)s',mode='w', level=logging.INFO, filters=('+ ***',), graph_style='default'):
    logging.basicConfig(level=level)
    hand = logging.FileHandler(filename=filename, mode=mode, encoding='utf-8')
    hand.setFormatter(logging.Formatter(fmt))
    logging.getLogger('').addHandler(hand)
    tracks.set_style(tracks._styles.get(graph_style, 'default'))
    for f in filters:
        address.append_filter(f)
    manager.refresh()
    _logging_enabled = True

def group_selector(event):
    return event.thread_name[0:4]
