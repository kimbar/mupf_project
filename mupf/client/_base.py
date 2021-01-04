import json
import queue
import weakref

import mupf.exceptions as exceptions

from .. import _command
from .. import _enhjson as enhjson
from .. import _features as F
from .. import _symbols as S
from .._remote import CallbackTask, RemoteObj
from ..log import loggable, LogManager

from . import _crrcan

async def send_task_body(wbs, json):
    log_sending_event('start', wbs, json)
    try:
        await wbs.send(json)
    except Exception as err:
        log_sending_event('mid', 'Exception:', err)
    finally:
        log_sending_event('end')

@loggable('client/base.py/*', log_results=False,)
def create_send_task(evl, wbs, json):
    evl.create_task(send_task_body(wbs, json))

@loggable(
    'client/base.py/*<obj>',
    log_path=False,
    long = lambda self: f"<{type(self).__name__} {getattr(self, '_cid', '?')[0:6]}>",
    long_det = lambda self: f"<{type(self).__name__} {getattr(self, '_cid', '?')[0:6]}>"
)
class Client:
    """
    Object represents a window of a browser.

    It is not called "Window", because `window` is already a top-level object of the JavaSript side, and this object is
    a little more than that. A `RemoteObj` of `window` can be easily obtained by `client.window`.
    """
    @loggable(log_results=False)
    def __init__(self, app, client_id):
        self._app_wr = weakref.ref(app)
        self._cid = client_id
        self._websocket = None
        self._user_agent = None
        self.features = set()
        self.enhjson_decoders = {
            "@": self.get_remote_obj,
        }
        self._callback_queue = queue.Queue()
        self._preconnection_stash = []
        self._healthy_connection = True    # FIXME: this should not start as True by default
        self.command = _command.create_command_class_for_client(self)
        self.window = RemoteObj(0, self)
        self._remote_obj_byid = weakref.WeakValueDictionary()
        self._clbid_by_callbacks = {}
        self._callbacks_by_clbid = {}
        self._callback_free_id = 0
        self._first_command = self.command('*first*')()    # ccid=0

    @loggable(log_results=False)
    def send_json(self, json):
        if not self._websocket:
            self._preconnection_stash.append(json)
        else:
            evl = self._app_wr()._event_loop
            json[3] = enhjson.EnhancedBlock(json[3])
            json = enhjson.encode(json, escape=self._escape_for_json)
            evl.call_soon_threadsafe(
                create_send_task,
                evl,
                self._websocket,
                json,
            )

    def _escape_for_json(self, value):
        """ Encoding advanced types for JSON transport

        This method is used by `mupf._enhjson.encode` to encode all types byond dicts, arrays, floats etc. It should
        return either a `enhjson.JsonElement` enum member or a tuple. The tuple is the escape structure for an advanced
        type (handler and arguments).

        We can here get a help from `enhjson.test_element_type()` function that will return an`enhjson.JsonElement` enum
        member if it can.
        """
        if isinstance(value, RemoteObj):
            return '@', value[S.rid]
        json_type = enhjson.test_element_type(value)
        if json_type == enhjson.JsonElement.Unknown:
            if callable(value):
                return '$', None, self._get_callback_id(value)
            else:
                # If we're here, `value` should have `.enh_json_esc()` method or fail
                return enhjson.JsonElement.Autonomous
        else:
            return json_type

    @loggable(log_enter=False)
    def __bool__(self):
        # for `while client:` syntax
        return self._healthy_connection

    @loggable()
    def decode_json(self, raw_json):
        msg = json.loads(raw_json)
        if F.core_features in self.features:
            msg[3] = enhjson.decode_enhblock(msg[3], self.enhjson_decoders)
        if msg[0] == 1 and msg[2] != 0:
            error_data = msg[3]['result']
            if line_id := self._app_wr()._identify_line_in_code(error_data[2:5]):
                error_data[2:5] = line_id
            msg[3]['result'] = exceptions.create_from_result(error_data)
        return msg

    @loggable()
    @classmethod
    def decode_json_simple(cls, raw_json):
        # called through class for `*first*`
        return json.loads(raw_json)

    @loggable()
    def get_remote_obj(self, rid, ctxrid=None):
        if rid == 0:
            return self.window
        # here a mutex - or maybe not... because this is always on eventloop anyway?
        if (rid, ctxrid) in self._remote_obj_byid:
            return self._remote_obj_byid[(rid, ctxrid)]
        else:
            if ctxrid is None:
                rem_obj = RemoteObj(rid, self, None)
            else:
                rem_obj = RemoteObj(rid, self, self.get_remote_obj(ctxrid))
            self._remote_obj_byid[(rid, ctxrid)] = rem_obj
            return rem_obj

    @loggable(log_results=False)
    def summoned(self):
        self._safe_dunders_feature = (F.safe_dunders in self.features)
        if F.strict_feature_list in self.features and self.features != self.app._features:
            raise ValueError(f'features computed {self.features} different from requested {self.app._features} while `strict_feature_list` feature turned on')

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
                # print(f'{time.time()-self.app._t0:.3f} -> [1,{c._ccid},1,{{"result":null}}]')
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
    def install_javascript(self, code=None, *, src=None, remove=True):
        if code is not None and src is None:
            return self.command('*install*')(code, remove=remove)
        elif src is not None and code is None:
            return self.command('*install*')(src=src, remove=remove)
        else:
            raise ValueError('you must provide just one of `code` or `src`')

    @loggable()
    def install_commands(self, code=None, src=None):
        self.install_javascript(code, src=src, remove=True).result
        if F.core_features in self.features:
            self.command._legal_names = self.command('*getcmds*')().result

    @loggable()
    def _get_callback_id(self, func):
        if func in self._clbid_by_callbacks:
            return self._clbid_by_callbacks[func]
        else:
            self._clbid_by_callbacks[func] = self._callback_free_id
            self._callbacks_by_clbid[self._callback_free_id] = func
            result = self._callback_free_id
            self._callback_free_id += 1
            return result

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
        return f"http://{self.app._host}:{self.app._port}/#{self.cid}"

@loggable('client/base.py/sending_event', hidden=True)
def log_sending_event(part, *args, **kwargs):
    pass


@loggable('client/base.py/send_task_body')
class LogSentTaskBody(LogManager):

    current_writer_id = None

    def on(self):
        count = self.employ_sentinels('client/base.py/sending_event')
        if count > 0:
            super().on()
        else:
            super().off()

    def off(self):
        self.dismiss_all_sentinels()
        super().off()

    def on_event(self, event):
        if self.state:
            if event.entering():
                finish = False
                if event.arg('part') == 'start':
                    wr = self.new_writer()
                    self.current_writer_id = wr.id_
                else:
                    wr = self.find_writer(id_=self.current_writer_id)
                    if event.arg('part') == 'end':
                        finish = True
                        self.delete_writer(self.current_writer_id)
                        self.current_writer_id = None
                wr.write(self.format_args(event.args[1:], event.kwargs), finish)
