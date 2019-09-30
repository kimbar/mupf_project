import asyncio
import copy
import inspect
import logging
import os
import re
import sys
import threading
import types

import websockets

# This must be before package imports or circular import occurs
MIN_COLUMN_WIDTH = 90    # minimum width of the column with names of functions
TAB_WIDTH = 20           # if the width is not enough, this much is added in one go
THREAD_TAB_WIDTH = 10    # the spacing for another thread graph column

from . import _address as address
from . import _tracks as tracks
from . import _manager as manager

lock = threading.Lock()
thread_number_by_threadid = {}    # FIXME: this is the old way of things -- to rethink
_logging_enabled = False

_filters = []


# TODO: move this to `_writer.py`
def just_info(*msg):
    """ Print a log line, but respecting the graph """
    logging.getLogger('mupf').info( "     "+tracks.write()+" ".join(map(str, msg)))

def enable(filename, fmt='[%(name)s] %(message)s',mode='w', level=logging.INFO, filters=('+ ***',), graph_style='default'):
    logging.basicConfig(level=level)
    hand = logging.FileHandler(filename=filename, mode=mode, encoding='utf-8')
    hand.setFormatter(logging.Formatter(fmt))
    logging.getLogger('').addHandler(hand)
    tracks._glyphs = tracks._styles.get(graph_style, 'default')
    for f in filters:
        address.append_filter(f)
    manager.refresh()
    _logging_enabled = True
