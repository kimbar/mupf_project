""" mupf 1.0.0 -- low-level browser DOM manipulation
╭─────────────────╮
│ ╭────────────── │
│ ├───┬───╮       │
│ │ │ │ │ │       │
│ │ ╰───╯         │
│ ├───╯           │
│ │               │
╰─────────────────╯
"""

# This is a HACK for developement purposes.
# If you do not have mupf-test-venv-helper module on your system you can
# safely ignore/delete this code.
try:
    import mupftestsvenvhelper
except ImportError:
    pass
else:
    mupftestsvenvhelper.repair_plugins(__path__)
    del mupftestsvenvhelper

# Log must be imported first, because it does a lot of its setup job during
# imports of all other modules (monkey-patching etc.)
from . import log

from ._app import App
from . import _symbols as S
from . import _features as F
from . import client    # This and following ones just to be explicit
from . import exceptions
from . import plugins

# Importing public modules from plugins directly into `mupf.`
from ._plugins_manager import inject, iterate_by_type
import types
inject(__name__, globals(), iterate_by_type, type_=types.ModuleType)
del types, iterate_by_type, inject
