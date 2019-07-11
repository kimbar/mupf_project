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

from . import _names as names
from . import _tracks as tracks
from . import _manager as manager

lock = threading.Lock()
thread_number_by_threadid = {}    # FIXME: this is the old way of things -- to rethink
_logging_enabled = False

_filters = []

MIN_COLUMN_WIDTH = 90    # minimum width of the column with names of functions
TAB_WIDTH = 20           # if the width is not enough, this much is added in one go
THREAD_TAB_WIDTH = 10    # the spacing for another thread graph column
rounded_graph_corners = True   # format of the graph ┌─ or ╭─

def just_info(*msg):
    """ Print a log line, but respecting the graph """
    logging.getLogger('mupf').info( "     "+tracks.write()+" ".join(map(str, msg)))

def enable(filename, fmt='[%(name)s] %(message)s',mode='w', level=logging.INFO, filters=('+ ***',)):
    logging.basicConfig(level=level)
    hand = logging.FileHandler(filename=filename, mode=mode, encoding='utf-8')
    hand.setFormatter(logging.Formatter(fmt))
    logging.getLogger('').addHandler(hand)
    for f in filters:
        names.append_filter(f)
    manager.refresh()
    _logging_enabled = True
