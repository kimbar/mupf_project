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

lock = threading.Lock()
thread_number_by_threadid = {}    # FIXME: this is the old way of things -- to rethink
_tracks = []
_logging_enabled = False
_short_class_repr = {}
_long_class_repr = {}
_filters = []

MIN_COLUMN_WIDTH = 90    # minimum width of the column with names of functions
TAB_WIDTH = 20           # if the width is not enough, this much is added in one go
THREAD_TAB_WIDTH = 10    # the spacing for another thread graph column
rounded_graph_corners = True   # format of the graph ┌─ or ╭─


def just_info(*msg):
    """ Print a log line, but respecting the graph """
    logging.getLogger('mupf').info( "     "+_repr_tracks()+" ".join(map(str, msg)))

def refresh():
    for l in LoggableFuncManager._loggables_by_name.values():
        if _should_be_on(l.name) == '+':
            l.on()
        else:
            l.off()

def enable(filename, fmt='[%(name)s] %(message)s',mode='w', level=logging.INFO, filters=('+ ***',)):
    global _short_class_repr, _logging_enabled
    logging.basicConfig(level=level)
    hand = logging.FileHandler(filename=filename, mode=mode, encoding='utf-8')
    hand.setFormatter(logging.Formatter(fmt))
    logging.getLogger('').addHandler(hand)
    for f in filters:
        _append_filter(f)
    refresh()
    _logging_enabled = True
