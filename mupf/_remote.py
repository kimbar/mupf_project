from . import _symbols as S
import weakref

class MetaRemoteObj(type):

    def __init__(cls, name, bases, dict_):
        super().__init__(name, bases, dict_)

    def __instancecheck__(self, instance):
        try:
            return instance[S.remote_obj_class]
        except Exception:
            return False

    def __subclasscheck__(self, instance):
        try:
            return instance[S.remote_obj_class]
        except Exception:
            return False      


class RemoteObj(metaclass=MetaRemoteObj):
    
    def __init__(self, rid, client, this=None):
        object.__setattr__(self, '_client_wr', weakref.ref(client))
        object.__setattr__(self, '_command_wr', weakref.ref(client.command))
        object.__setattr__(self, '_rid', rid)
        object.__setattr__(self, '_this', this)
        object.__setattr__(self, '_json_esc_interface', RemoteJsonEsc(rid))

    def __setitem__(self, key, value):
        if isinstance(key, S._Symbol):
            if key.readonly:
                raise AttributeError('Attribute `{}` is readonly'.format(key))
            else:
                object.__setattr__(self, key.internal_name, value)
        else:
            object.__getattribute__(self, '_command_wr')()('*seti*')(self[S.json_esc_interface], key, value).result

    def __getitem__(self, key):
        if isinstance(key, S._Symbol):
            # if key == S.dunder_class:
            #     # This is if you reaeaeally need to access `.__class__` on the JS side
            #     return self[S.command_wr]()('*get*')(self[S.json_esc_interface], "__class__").result
            return object.__getattribute__(self, key.internal_name)
        else:
            return object.__getattribute__(self, '_command_wr')()('*geti*')(self[S.json_esc_interface], key).result

    def __setattr__(self, key, value):
        if not isinstance(value, RemoteObj) and callable(value):
            value = object.__getattribute__(self, '_client_wr')()._wrap_callback(value)
        object.__getattribute__(self, '_command_wr')()('*set*')(self[S.json_esc_interface], key, value).wait

    def __getattribute__(self, key):
        if self[S.client_wr]()._safe_dunders_feature and key == "__class__":    # __dict__ __bases__ __name__ __qualname__ __mro__ __subclasses__
            # this allows for `isinstance()` for `RemoteObj`
            return RemoteObj
        return self[S.command_wr]()('*get*')(self[S.json_esc_interface], key).result

    def __call__(self, *args):
        this = _make_escapable(self[S.this])
        args = map(_make_escapable, args)
        return object.__getattribute__(self, '_command_wr')()('*call*')(*args, id=self[S.rid], this_=this).result

    def __del__(self):
        command = object.__getattribute__(self, '_command_wr')()
        # 1. some mutex here? because `command` may dissapear
        rid = self[S.rid]
        if command is not None and rid != 0 and self[S.client_wr]()._healthy_connection:    # do not try to GC the `window`
            command('*gc*').run(rid).result

    @property
    def _client(self):
        return  self[S.client_wr]()

    def _remote_obj_class(self):
        return True


class RemoteJsonEsc:
    def __init__(self, rid):
        self.rid = rid
    def json_esc(self):
        return '@', self.rid
    def __repr__(self):
        return '["~@",{}]'.format(self.rid)


class CallbackTask:

    def __init__(self, client, ccid, func, args):
        self._client = client
        self._ccid = ccid
        self._func = func
        self._args = args

    def run(self):
        answer = self._func(*self._args)
        self._client.send_json([6, self._ccid, 0, answer])


class CallbackJsonEsc:
    def __init__(self, clbid):
        self.clbid = clbid
    def json_esc(self):
        return '$', None, self.clbid
    def __repr__(self):
        return '["~$",null,{}]'.format(self.clbid)


def _make_escapable(value):
    try:
        return value[S.json_esc_interface]
    except Exception:
        return value
