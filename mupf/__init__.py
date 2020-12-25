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

from ._app import App
from . import _symbols as S
from . import _features as F
