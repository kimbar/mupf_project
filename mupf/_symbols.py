from ._utils import removeprefix as _removeprefix

class _Symbol:
    def __init__(self, internal_name, *, readonly=False, weakref=False):
        self.internal_name = internal_name
        self.readonly = readonly
        self.weakref = weakref

    def __eq__(self, other):
        return self.internal_name == other.internal_name

    def __hash__(self):
        return hash(self.internal_name)

    def __repr__(self):
        return f"[Symbol: {_removeprefix(self.internal_name, '_')}]"


# Underlines on the begining of the internal names are here because these internal names are used as private properties
# of `RemoteObj`, not because there is some requirement for `_Symbol`
#
this = _Symbol("_this", readonly=True)
rid = _Symbol("_rid", readonly=True)
client = _Symbol("_client", readonly=True, weakref=True)
command = _Symbol("_command", readonly=True, weakref=True)

def __getattr__(name: str) -> _Symbol:
    return _Symbol('_'+name)
