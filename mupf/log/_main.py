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
    """ Enable logging

    This should be called once after setting appropriate values in the
    `settings` module.
    """
    global _logging_enabled, _default_all_on
    # Are all managers "on" by default or "off"
    _default_all_on = default_all_on
    # Setting up the `logging` built-in module on which this logging is based
    logging.basicConfig(level=settings.logging_level)
    hand = logging.FileHandler(filename=file_name, mode=file_mode, encoding='utf-8')
    hand.setFormatter(logging.Formatter(settings.logging_format))
    logging.getLogger('').addHandler(hand)
    # Setting up the style for tracks
    _tracks.set_style(_tracks._styles.get(settings.graph_style, 'default'))
    # Enabling logging
    with log_mutex:
        _logging_enabled = True
        _manager.refresh()

def disable():
    # TODO: This is experimental, or a placeholder. The enbling/disabling procedure
    # should be rethought and developed with "channels" feature. "Channels"
    # will be different streams (files) for different purposes. Future feature.
    global _logging_enabled
    _logging_enabled = False

def add_filters(*args, **kwargs):
    """ Add filters deciding which managers should be on

    Filters are strings in format `"<marker> <address pattern>"`. `<marker>` is one of the `"+"`, `"-"` or `"#"`
    characters. `<address pattern>` is a simplified regular expression, similar to those used in system shells. The
    pattern should "match" some addresses of the managers (it can be just an address of a single manager.) If the
    pattern matches `<marker>` decides if the manager should be switched on (`"+"`) or off (`"+"`). Filters with `"#"`
    are not used (are commented.) Filters are matched in the sequence they were added.  For each manager, the last
    filter matched (and not commented) decides of the state of the manager.

    Filters should be passed as unnamed or named. The advantege of naming a filter is that one can change its state
    (`<marker>`) later on. For example:

    ```
    add_filters("+ app.py/**", dj="# **/Client.decode_json")
    ```

    First filter is unnamed, second one is named and can be changed:

    ```
    set_filter_state(dj="+")
    ```

    Currently it is impossible to change order or delete the filters (commenting is the closest to deletion right now.)
    """
    with log_mutex:
        for filter_ in args:
            _address.append_filter(filter_)
        for handle, filter_ in kwargs.items():
            _address.append_filter(filter_, handle)

def set_filters_state(**kwargs):
    """ Changes the marker of a named filter

    If a filter was named in `add_filters` its marker (state) can be changed here.
    Refer to the `add_filters` documentation for details.
    """
    with log_mutex:
        global _filters
        for handle, state in kwargs.items():
            _filters[handle][0] = state[0]
        _manager.refresh()

def group_selector(event):
    return event.thread_name[0:settings.GROUP_NAME_WIDTH]
