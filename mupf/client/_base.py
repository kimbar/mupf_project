import weakref
from .._command import create_command_class_for_client
import mupf.exceptions as exceptions
import time
from .._remote import RemoteObj
from .. import _symbols as S
from .. import _features as F
import json
from .. import _enhjson as enhjson

async def send_task_body(wbs, json):
    await wbs.send(json)

def create_send_task(evl, wbs, json):
    evl.create_task(send_task_body(wbs, json))

class Client:
    """
    Object represents a window of a browser.

    It is not called "Window", because `window` is already a top-level object of the JavaSript side, and this object is
    a little more than that. A `RemoteObj` of `window` can be easily obtained by `client.window`.
    """
    def __init__(self, app, client_id):
        self._app_wr = weakref.ref(app)
        self._cid = client_id
        self._websocket = None
        self._user_agent = None
        self.features = set()
        self.enhjson_decoders = {
            "~@": self.get_remote_obj,
        }
        self._preconnection_stash = []
        self._healthy_connection = True
        self._safe_dunders_feature = False
        self.command = create_command_class_for_client(self)
        self.window = RemoteObj(0, self)
        self._remote_obj_byid = weakref.WeakValueDictionary()
        self._first_command = self.command('*first*')()    # ccid=0

    def send_json(self, json):
        if not self._websocket:
            self._preconnection_stash.append(json)
        else:
            evl = self.app._event_loop
            json[3] = enhjson.EnhancedBlock(json[3]) 
            evl.call_soon_threadsafe(
                create_send_task,
                evl,
                self._websocket,
                enhjson.encode(json),
            )

    def __bool__(self):
        # for `while client:` syntax
        return self._healthy_connection

    def decode_json(self, raw_json):
        if self is None:
            return json.loads(raw_json)    # called through class for `*first*`
        msg = json.loads(raw_json)
        if F.core_features in self.features:
            msg[3] = enhjson.decode(msg[3], self.enhjson_decoders)
        if msg[0] == 1 and msg[2] != 0:
            msg[3]['result'] = exceptions.create_from_result(msg[3]['result'])
        return msg

    def get_remote_obj(self, *args):
        rid = args[0]
        ctxrid = args[1] if len(args)>1 else None
        if rid == 0:
            return self.window
        elif rid is None:
            return None
        # here a mutex - or maybe not... because this is always on eventloop anyway?
        if (rid, ctxrid) in self._remote_obj_byid:
            return self._remote_obj_byid[(rid, ctxrid)]
        else:
            rem_obj = RemoteObj(rid, self, self.get_remote_obj(ctxrid))
            self._remote_obj_byid[(rid, ctxrid)] = rem_obj
            return rem_obj

    def summoned(self):
        self._safe_dunders_feature = (F.safe_dunders in self.features)
        if F.strict_feature_list in self.features and self.features != self.app._features:
            raise ValueError('features computed {} different from requested {} while `strict_feature_list` feature turned on'.format(self.features, self.app._features))

    def _command_hnd(self, data):
        if data['error']:
            self.command.resolve_by_id_mupf(ccid=data['ccid'], result=exceptions.create_from_result(data['result']))
        else:    
            self.command.resolve_by_id_mupf(ccid=data['ccid'], result=data['result'])

    def _notification_hnd(self, data):
        pass

    def _callback_hnd(self, data):
        pass

    def close(self, dont_wait=False):   # TODO: dont_wait not implemented
        # Mutex here to set this and issue `*last*` atomicly?
        self._healthy_connection = False
        # wait for previous commands (or maybe this is not needed since we're waiting for `*last*.result` anyway?)
        try:
            c = self.command('*last*')()  # to consider: can an exception be rised in this line or only in next one? what consequences this have? and for other commands than `*last*`?
            c.result    # TODO: maybe here as a parameter should the number of hanging commands been passed?, but obtaining their count... heavy mutexing needed...
        except exceptions.ClientClosedNormally:   # TODO: this exception change for a timeout
            print('{:.3f} ->'.format(time.time()-self.app._t0), '[1,{0},1,{{"result":null}}]'.format(c._ccid))
            del self.app._clients_by_cid[self._cid]

    def await_connection(self):
        if self._first_command:
            self._first_command.wait
            if self._first_command.is_in_bad_state():
                pass
            self._first_command = None
        for json in self._preconnection_stash:
            self.send_json(json)
        self._preconnection_stash.clear()
        return self

    def install_javascript(self, code=None, src=None, remove=True):
        if code is not None and src is None:
            return self.command('*install*')(code, remove=remove)
        elif src is not None and code is None:
            return self.command('*install*')(src=src, remove=remove)
        else:
            raise ValueError('you must provide just one of `code` or `src`')
    
    def install_commands(self, code=None, src=None):
        self.install_javascript(code, src, remove=True).result
        if F.core_features in self.features:
            self.command._legal_names = self.command('*getcmds*')().result

    @property
    def app(self):
        return self._app_wr()

    @property
    def cid(self):
        return self._cid

    @property
    def url(self):
        return "http://{domain}:{port}/#{cid}".format(
                domain = self.app._host,
                port = self.app._port,
                cid = self.cid,
            )

        