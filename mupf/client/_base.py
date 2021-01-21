import json
import queue
import weakref

import mupf.exceptions as exceptions
import time

from .. import _command
from .. import _enhjson as enhjson
from .. import _features as F
from .. import _symbols as S
from .._remote import CallbackTask, RemoteObj
from ..log import loggable, LogManager

from . import _crrcan

from .._srvthr import Client_SrvThrItf


@loggable(
    'client/base.py/*<obj>',
    log_path=False,
    long = lambda self: f"<{type(self).__name__} {getattr(self, '_cid', '?')[0:6]}>",
    long_det = lambda self: f"<{type(self).__name__} {getattr(self, '_cid', '?')[0:6]}>"
)
class Client(Client_SrvThrItf):
    """
    Object of this class represents a window of a browser.

    It is not called "Window", because ``window`` is already a top-level object of the JS-side, and this object is a
    little more than that. A :class:`~mupf._remote.RemoteObj` of ``window`` can be obtained by :attr:`window`.

    """
    @loggable(log_results=False)
    def __init__(self, app, client_id):
        self._app_wr = weakref.ref(app)
        self._cid = client_id
        app._clients_by_cid[client_id] = self

        self._user_agent = None
        self.features = set()
        self.enhjson_decoders = {
            "@": self.get_remote_obj,
        }
        self._callback_queue = queue.Queue()

        self._healthy_connection = True    # FIXME: this should not start as True by default
        self.command = _command.create_command_class_for_client(self)
        """ A ``command`` class used in command invoking syntax. """

        self.window = RemoteObj(0, self)
        """ A :class:`~mupf._remote.RemoteObj` object representing the ``window`` object on the JS-side. """

        self._remote_obj_byid = weakref.WeakValueDictionary()
        self._clbid_by_callbacks = {}
        self._callbacks_by_clbid = {}
        self._callback_free_id = 0
        Client_SrvThrItf.__init__(self)

        # This callback unblocks `self.run_one_callback_blocking()`, otherwise the goggles - do nothing.
        self._get_callback_id(log_debug, '*close*')

    def _send(self, data):
        if F.core_features in self.features:
            data[3] = enhjson.EnhancedBlock(data[3])
        data = enhjson.encode(data, escape=self._escape_for_json)
        Client_SrvThrItf._send(self, data)

    def _escape_for_json(self, value):
        """ Encoding advanced types for JSON transport

        This method is used by :func:`mupf._enhjson.encode` to encode all types byond dicts, arrays, floats etc. It
        should return either a :class:`enhjson.JsonElement` enum member or a tuple. The tuple is the escape structure
        for an advanced type (handler and arguments).

        We can here get a help from :func:`enhjson.test_element_type` function that will return a
        :class:`enhjson.JsonElement` enum member if it can.
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
    def _decode_crrcan_msg(self, raw_json):
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
    def get_remote_obj(self, rid, ctxrid=None):
        if rid == 0:
            return self.window
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
        if self._healthy_connection:
            # This command triggers the closing of the websocket connection in normal way.
            last_cmd_ccid = self.command('*last*')().result
        if not _dont_remove_from_app:
            del self.app._clients_by_cid[self._cid]

    @loggable()
    def await_connection(self):
        pass

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
    def _get_callback_id(self, func, clbid=None):
        if func in self._clbid_by_callbacks:
            return self._clbid_by_callbacks[func]
        else:
            if clbid is None:
                clbid = self._callback_free_id
                self._callback_free_id += 1
            elif clbid in self._callbacks_by_clbid:
                raise ValueError(f'Callback id `{clbid!r}` already in use for callback `{self._callbacks_by_clbid[clbid]!r}`')
            self._clbid_by_callbacks[func] = clbid
            self._callbacks_by_clbid[clbid] = func
            return clbid

    @loggable()
    def run_one_callback_blocking(self):
        if not self._healthy_connection:
            self.run_callbacks_nonblocking()    # This is to run all notifications (callbacks will be supressed)
            return
        callback_task = self._callback_queue.get(block=True)
        callback_task.run()

    @loggable()
    def run_callbacks_nonblocking(self, count_limit=None, time_limit=None):
        t0 = time.time()
        count = 0
        while True:
            if (
                   (time_limit is not None and time.time() >= t0+time_limit)
                or (count_limit is not None and count >= count_limit)
                ):
                break
            try:
                callback_task = self._callback_queue.get_nowait()
            except queue.Empty:
                break
            else:
                callback_task.run(only_notifications = not self._healthy_connection)
                count += 1

    @loggable()
    def run_callbacks_blocking_until_closed(self, silent_user_close=True):
        # if silent_user_close try/except ClosedUnexpectedly etc...
        while self:
            self.run_one_callback_blocking()


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
        return f"http://{self.app._host}:{self.app._port}/mupf/{self.cid}/"

    def _get_eventloop(self):
        return self._app_wr()._event_loop


@loggable('client/base.py/debug')
def log_debug(*args, **kwargs):
    pass

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
