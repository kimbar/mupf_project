import weakref
from .._command import create_command_class_for_client
import mupf.exceptions as exceptions
import time
from .._remote import RemoteObj, CallbackJsonEsc, CallbackTask
from .. import _symbols as S
from .. import _features as F
import json
from .. import _enhjson as enhjson
import queue

from .._logging import loggable

async def send_task_body(wbs, json):
    log_sending_event('sending...', wbs, json)
    await wbs.send(json)
    log_sending_event('sent')

@loggable('client/base_py/*')
def create_send_task(evl, wbs, json):
    evl.create_task(send_task_body(wbs, json))

@loggable('client/base_py/*<>', log_path=False)
class Client:
    """
    Object represents a window of a browser.

    It is not called "Window", because `window` is already a top-level object of the JavaSript side, and this object is
    a little more than that. A `RemoteObj` of `window` can be easily obtained by `client.window`.
    """
    @loggable()
    def __init__(self, app, client_id):
        self._app_wr = weakref.ref(app)
        self._cid = client_id
        self._websocket = None
        self._user_agent = None
        self.features = set()
        self.enhjson_decoders = {
            "~@": self.get_remote_obj,
        }
        self._callback_queue = queue.Queue()
        self._preconnection_stash = []
        self._healthy_connection = True
        self._safe_dunders_feature = False
        self.command = create_command_class_for_client(self)
        self.window = RemoteObj(0, self)
        self._remote_obj_byid = weakref.WeakValueDictionary()
        self._clbid_by_callbacks = {}
        self._callbacks_by_clbid = {}
        self._callback_free_id = 0
        self._first_command = self.command('*first*')()    # ccid=0

    @loggable()
    def send_json(self, json):
        if not self._websocket:
            self._preconnection_stash.append(json)
        else:
            evl = self._app_wr()._event_loop
            json[3] = enhjson.EnhancedBlock(json[3]) 
            json = enhjson.encode(json)
            # print('<- {:.3f}'.format(time.time()-self._app_wr()._t0), json)
            evl.call_soon_threadsafe(
                create_send_task,
                evl,
                self._websocket,
                json,
            )

    @loggable(log_enter=False)
    def __bool__(self):
        # for `while client:` syntax
        return self._healthy_connection

    @loggable()
    def decode_json(self, raw_json): 
        msg = json.loads(raw_json)
        if F.core_features in self.features:
            msg[3] = enhjson.decode(msg[3], self.enhjson_decoders)
        if msg[0] == 1 and msg[2] != 0:
            msg[3]['result'] = exceptions.create_from_result(msg[3]['result'])
        return msg

    @loggable()
    @classmethod
    def decode_json_simple(cls, raw_json):
        # called through class for `*first*`
        return json.loads(raw_json)

    @loggable()
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

    @loggable()
    def summoned(self):
        self._safe_dunders_feature = (F.safe_dunders in self.features)
        if F.strict_feature_list in self.features and self.features != self.app._features:
            raise ValueError('features computed {} different from requested {} while `strict_feature_list` feature turned on'.format(self.features, self.app._features))

    @loggable()
    def close(self, dont_wait=False, _dont_remove_from_app=False):   # TODO: dont_wait not implemented
        # Mutex here to set this and issue `*last*` atomicly?
        if self._healthy_connection:
            self._healthy_connection = False
            # wait for previous commands (or maybe this is not needed since we're waiting for `*last*.result` anyway?)
            try:
                c = self.command('*last*')()  # to consider: can an exception be rised in this line or only in next one? what consequences this have? and for other commands than `*last*`?
                c.result    # TODO: maybe here as a parameter should the number of hanging commands been passed?, but obtaining their count... heavy mutexing needed...
            except exceptions.ClientClosedNormally:   # TODO: this exception change for a timeout
                # print('{:.3f} ->'.format(time.time()-self.app._t0), '[1,{0},1,{{"result":null}}]'.format(c._ccid))
                pass

        if not _dont_remove_from_app:
            del self.app._clients_by_cid[self._cid]

    @loggable()
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

    @loggable()
    def install_javascript(self, code=None, src=None, remove=True):
        if code is not None and src is None:
            return self.command('*install*')(code, remove=remove)
        elif src is not None and code is None:
            return self.command('*install*')(src=src, remove=remove)
        else:
            raise ValueError('you must provide just one of `code` or `src`')
    
    @loggable()
    def install_commands(self, code=None, src=None):
        self.install_javascript(code, src, remove=True).result
        if F.core_features in self.features:
            self.command._legal_names = self.command('*getcmds*')().result
    
    @loggable()
    def _wrap_callback(self, func):
        if func in self._clbid_by_callbacks:
            return CallbackJsonEsc(self._clbid_by_callbacks[func])
        
        self._clbid_by_callbacks[func] = self._callback_free_id
        self._callbacks_by_clbid[self._callback_free_id] = func
        
        res = CallbackJsonEsc(self._callback_free_id)
        self._callback_free_id += 1
        return res

    @loggable()
    def shedule_callback(self, ccid, noun, pyld):
        self._callback_queue.put(CallbackTask(self, ccid, noun, pyld))
    
    @loggable()
    def run_one_callback_blocking(self):
        if not self._healthy_connection:
            return
        callback_task = self._callback_queue.get(block=True)
        callback_task.run()

    @property
    @loggable('*.:', log_enter=False)
    def app(self):
        return self._app_wr()

    @property
    @loggable('*.:', log_enter=False)
    def cid(self):
        return self._cid

    @property
    @loggable('*.:', log_enter=False)
    def url(self):
        return "http://{domain}:{port}/#{cid}".format(
                domain = self.app._host,
                port = self.app._port,
                cid = self.cid,
            )

    def __repr__(self):
        return "<{} {}>".format(type(self).__name__, getattr(self, '_cid', '?')[0:6])

@loggable('client/base_py/sending_event', log_exit=False)
def log_sending_event(*args, **kwargs):
    pass