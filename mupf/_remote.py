from . import _symbols as S
import weakref
import re
from ._enhjson import IJsonEsc

from .log import loggable

class FinalClass(type):

    def __init__(cls, name, bases, dict_):
        if len(bases):
            raise RuntimeError(f"`{bases[0]}` is final -- cannot be subclassed")
        super().__init__(name, bases, dict_)

_re_dunder = re.compile(r'^__[^_]+__$')

class RemoteObj(metaclass=FinalClass):

    def __init__(self, rid, client, this=None):
        object.__setattr__(self, S.client.internal_name, weakref.ref(client))
        object.__setattr__(self, S.command.internal_name, weakref.ref(client.command))
        object.__setattr__(self, S.rid.internal_name, rid)
        object.__setattr__(self, S.this.internal_name, this)

    def __getattribute__(self, key):
        """ Interface for `obj.key` syntax

        All `key` except "dunders" are translated to JS-side attributes.
        "Dunders" (eg. `__class__`, `__qualname__` etc.) are always
        Python-side, that is they refer directly to `RemoteObj` object, not to
        its JS-side counterpart.

        If a JS-side reference of a "dunder" is needed it can always be
        achieved with `__getitem__` syntax, that is `obj["__class__"]`.
        """
        if _re_dunder.match(key):
            return object.__getattribute__(self, key)
        return object.__getattribute__(self, '_command')()('*get*')(self, key).result

    def __setattr__(self, key, value):
        """ Interface for `obj.key = value` syntax

        See description for `__getattribute__` for details.
        """
        if _re_dunder.match(key):
            object.__setattr__(self, key, value)
        else:
            object.__getattribute__(self, '_command')()('*set*')(self, key, value).wait

    def __getitem__(self, key):
        """ Interface for `obj[key]` syntax

        All `key` exept `_Symbol` are translated to JS-side attributes.
        `_Symbol` are resolved on the Py-side, automatically stripped of
        `weakref` if needed.
        """
        if isinstance(key, S._Symbol):
            item = object.__getattribute__(self, key.internal_name)
            return item() if key.weakref else item
        else:
            return object.__getattribute__(self, '_command')()('*get*')(self, key).result

    def __setitem__(self, key, value):
        """ Interface for `obj[key] = value` syntax

        See description for `__getitem__` for details. If a `_Symbol` attribute
        is readonly an `AttributeError` is risen.
        """
        if isinstance(key, S._Symbol):
            if key.readonly:
                raise AttributeError(f'Attribute `{key}` is readonly')
            elif key.weakref:
                object.__setattr__(self, key.internal_name, weakref.ref(value))
            else:
                object.__setattr__(self, key.internal_name, value)
        else:
            object.__getattribute__(self, '_command')()('*set*')(self, key, value).result

    def __call__(self, *args):
        """ Interface for `obj(arg1, arg2, ...)` syntax

        A function call is made on the JS-side.
        """
        return object.__getattribute__(self, '_command')()('*call*')(
            *args,
            id = object.__getattribute__(self, '_rid'),
            this_ = object.__getattribute__(self, '_this'),
        ).result

    def __repr__(self):
        client = object.__getattribute__(self, '_client')()
        return f"<RemoteObj ~@{object.__getattribute__(self, '_rid')} of {getattr(client, '_cid', '?')[0:6]}>"

    def __del__(self):
        command = self[S.command]
        # 1. some mutex here? because `command` may dissapear
        rid = self[S.rid]
        if command is not None and rid != 0 and self[S.client]._healthy_connection:    # do not try to GC the `window`
            command('*gc*').run(rid).result


@loggable(
    'remote.py/*<obj>',
    short = lambda self: f"<{getattr(self, '_ccid', '?')}>",
    long = lambda self: f"<CallbackTask {getattr(self, '_noun', '?')} {getattr(self, '_ccid', '?')} {getattr(self, '_func', '-')}>"
)
class CallbackTask:
    # TODO: this is very much a work in progress, serious rethinking
    # of this class is needed

    @loggable()
    def __init__(self, client, ccid, noun, pyld):
        self._client = client
        self._ccid = ccid
        self._noun = noun
        self._args = None
        if isinstance(noun, int):
            self._func = client._callbacks_by_clbid[noun]
            self._noun = None
            self._args = pyld['args']

    @loggable()
    def run(self):
        if self._noun is None:
            answer = self._func(*self._args)
            self._client.send_json([6, self._ccid, 0, answer])
            return
        if self._noun == '*close*':
            return
