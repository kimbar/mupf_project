from . import _symbols as S
import weakref
import re

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
        object.__setattr__(self, S.json_esc_interface.internal_name, RemoteJsonEsc(rid))

    def __getattribute__(self, key):
        """ Interface for `obj.key` syntax

        All `key` except "dunders" are translated to JS-side attributes.
        "Dunders" (eg. `__class__`, `__qualname__` etc.) are always
        Python-side, that is they refer directly to `RemoteObj` object, not to
        its JS-side counterpart.

        If a JS-side reference of a "dunder" is needed it can always be
        achieved with `__getitem__` syntax, that is `obj["__class__"]`.
        """
        # print(f"__getattribute__ {repr(key)}")
        if _re_dunder.match(key):
            return object.__getattribute__(self, key)
        # print(f"__getattribute__ {key} -> sending *get*")
        return object.__getattribute__(self, '_command')()('*get*')(
            object.__getattribute__(self, '_json_esc_interface'),
            key,
        ).result

    def __setattr__(self, key, value):
        """ Interface for `obj.key = value` syntax

        All `key` are set at the JS-side (even the "dunders"). If value is a
        callable it is registered at the client and only a reference is sent to
        the JS-side.
        """
        # if value.__class__ != RemoteObj and callable(value):
        #     value = CallbackJsonEsc(object.__getattribute__(self, '_client')()._get_callback_id(value))
        object.__getattribute__(self, '_command')()('*set*')(
            object.__getattribute__(self, '_json_esc_interface'),
            key,
            value,
        ).wait

    def __getitem__(self, key):
        # print(f"__getitem__ {key}")
        if isinstance(key, S._Symbol):
            item = object.__getattribute__(self, key.internal_name)
            if key.weakref:
                return item()
            else:
                return item
        else:
            return object.__getattribute__(self, '_command')()('*seti*')(
                object.__getattribute__(self, '_json_esc_interface'),
                key,
            ).result

    def __setitem__(self, key, value):
        # print(f"__setitem__ {key}")
        if isinstance(key, S._Symbol):
            if key.readonly:
                raise AttributeError(f'Attribute `{key}` is readonly')
            else:
                object.__setattr__(self, key.internal_name, value)
        else:
            # if value.__class__ != RemoteObj and callable(value):
            #     value = CallbackJsonEsc(object.__getattribute__(self, '_client')()._get_callback_id(value))
            object.__getattribute__(self, '_command')()('*seti*')(
                object.__getattribute__(self, '_json_esc_interface'),
                key,
                value,
            ).result

    # Is the `_make_escapable` really reqired here? It should be done in
    # `_enhjson.py` anyway?
    def __call__(self, *args):
        return object.__getattribute__(self, '_command')()('*call*')(
            *map(_make_escapable, args),
            id = object.__getattribute__(self, '_rid'),
            this_ = _make_escapable(object.__getattribute__(self, '_this')),
        ).result

    def __repr__(self):
        client = object.__getattribute__(self, '_client')()
        return f"<Remote ~@{object.__getattribute__(self, '_rid')} of {type(client).__name__} {getattr(client, '_cid', '?')[0:6]}>"

    def __del__(self):
        # print(f"__del__")
        command = self[S.command]
        # 1. some mutex here? because `command` may dissapear
        rid = self[S.rid]
        # print(f"__del__ rid = {rid}")
        if command is not None and rid != 0 and self[S.client]._healthy_connection:    # do not try to GC the `window`
            # print(f"__del__ rid = {rid} command *gc*")
            command('*gc*').run(rid).result


class RemoteJsonEsc:
    def __init__(self, rid):
        self.rid = rid
    def json_esc(self):
        return '@', self.rid
    def __repr__(self):
        return f'["~@",{self.rid}]'


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


def _make_escapable(value):
    try:
        return value[S.json_esc_interface]
    except Exception:
        return value


loggable(
    outer_class = RemoteObj,
    long = lambda self: f"<RemoteObj {self[S.rid]} of {self[S.client]._cid[0:6]} at {id(self):X}>",
)
