import asyncio
import base64
import mimetypes
import os
import sys
import threading
import time
import typing as T
import urllib
import uuid
from http import HTTPStatus

import pkg_resources
import websockets

from . import _features as F
from . import client, exceptions
from ._macro import MacroByteStream
from . import log
from .log import loggable, loggable_class

from ._srvthr import App_SrvThrItf


@loggable(
    'app.py/*<obj>',
    log_path = False,
    short = lambda self: f"<{id(self):X}>",
    long = lambda self: f"<App {id(self):X}>",
)
class App(App_SrvThrItf):
    """
    Class for an app. Object represents a server and port, and a thread with an event-loop.

    There is a little reason to have more than one object of this class in the process, however there may be periods in
    process execution when GUI is not needed. Destruction of this object represents destruction of GUI. This feature
    would be inconvenient if the API of this class was present directly in the `mupf` package namespace.
    """

    default_port = 57107

    @loggable()
    def __init__(
        self,
        host: str ='127.0.0.1',
        port: int = default_port,
        charset: str ='utf-8',
        features: T.Iterable[F._features__Feature]= (),
    ):
        self._t0: float = time.time()
        self._host: str = host
        self._port: int = port
        self._charset: str = charset
        self._features: set[F._features__Feature] = set()

        # Checking the format of `features` argument.  Tested in `vanilla_env/test_featyres.py/Features`
        try:
            feat_type_check = any([not isinstance(f, F.__dict__['__Feature']) for f in features])
        except Exception:
            raise TypeError("`feature` argumnet of `App` must be a **container** of features")
        if feat_type_check:
            raise TypeError("all features must be of `mupf.F.__Feature` type")

        # Features are added in reverse order than listed in `features`, because of the semantics of `set()` creator -
        # doing nothing when an element already exists. The features are hashed by their names only (not name and state)
        # This way stored state of a feature is taken from the last occurence of a given feature on the list.
        self._features = set(reversed(features))
        # `.update()` has the same semantics as creator, so only features not on the list are added (with their default
        # states).
        self._features.update(F.feature_list)
        self._features = set(filter(lambda f: f.state, self._features))

        self._clients_by_cid: dict[str, client.Client] = {}
        self._root_path: str = os.path.split(sys.argv[0])[0]
        self._file_routes: dict[str, str] = {}

        self._clients_generated = 0
        App_SrvThrItf.__init__(self)

    @loggable()
    def get_unique_client_id(self) -> str:
        if log.settings.deterministic_identificators:
            self._clients_generated += 1
            return f"cl{self._clients_generated:>04}abcdefghABCDEFGH"
        while True:
            # This should be HTTP cookie safe. It is hence it is `[-_0-9A-Za-z]+`
            cid = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=')
            if '-' not in cid[0:6]:
                for used_cid in self._clients_by_cid:
                    if cid[0:6] == used_cid[0:6]:
                        break
                else:
                    break
        self._clients_generated += 1
        return cid

    @loggable()
    def summon_client(self, frontend: client.Client = client.WebBrowser, **kwargs) -> client.Client:
        client = frontend(self, self.get_unique_client_id(), **kwargs)
        client.install_javascript(src='mupf/core').wait
        for feat, state in client.command('*features*')().result.items():
            if state:
                client.features.add(+getattr(F, feat))
        if F.core_features in client.features:
            client.command._legal_names.append('*getcmds*')
            client.command._legal_names = client.command('*getcmds*')().result
        client.summoned()
        return client

    @loggable()
    def __enter__(self):
        if not self.is_closed():
            return self._clients_by_cid[list(self._clients_by_cid.keys())[0]]
        else:
            self.open()
            if culprit := self.is_closed(get_culprit=True):
                raise culprit
            return self

    @loggable()
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if exc_value is not None:
            raise exc_value

    @loggable()
    def open(self):
        self._server_thread = threading.Thread(
            target = self._server_thread_body,
            daemon = False,
            name = f"mupfapp-{self._host}:{self._port}"
        )
        self._server_thread.start()
        self._server_opened_mutex.wait()
        return self

    @loggable(log_results=False)
    def open_with_client(self, frontend=client.WebBrowser, **kwargs):
        self.__enter__()
        self.summon_client(frontend, **kwargs)
        return self

    @loggable()
    def is_closed(self, get_culprit: bool = False) -> T.Union[bool, BaseException]:
        """ Is app closed?

        It returns `False` if it is not closed. Otherwise it returns `True` by default or an exception if asked for the
        culprit of the app being closed. The exception is not rised - it is only returned and must be rised outside.
        """
        if get_culprit:
            if not self.is_closed():
                return False
            elif isinstance(self._event_loop, asyncio.events.AbstractEventLoop):
                return RuntimeError(f'Event loop in `{self}` was closed')
            elif self._event_loop is None:
                # It's hard to give a reason, because this should never happen (FLW) unless user creates App, does not
                # open it and asks why it is closed.
                return RuntimeError(f'Event loop in `{self}` was never created (`App` was never opened?)')
            else:
                return self._event_loop # if event-loop is not opened this is an exception
        else:
            if isinstance(self._event_loop, asyncio.events.AbstractEventLoop):
                return self._event_loop.is_closed()
            else:
                return True

    @loggable()
    def _get_client_by_cid(self, cid):
        return self._clients_by_cid[cid]

    @loggable()
    def close(self, wait=False):
        for cl in self._clients_by_cid.values():
            cl.close(_dont_remove_from_app=True)
        self._clients_by_cid.clear()
        self._event_loop.call_soon_threadsafe(self._event_loop.stop)
        if wait:
            self._server_closed_mutex.wait()

#region It's a mess

    # The serving of so-called static files become quite a mess. It is because this subsystem was never really designed
    # as a whole. Right now it consists of following parts:
    #
    #  * mupf.App._process_HTTP_request
    #  * mupf.App.register_route
    #  * mupf.App._get_route_response
    #  * mupf.App._identify_line_in_code
    #  * mupf.client.Client.decode_json
    #  * mupf.exceptions.create_from_result
    #  * mupf._macro.MacroByteStream
    #  * mupf.F.__Feature
    #

    @loggable()
    def _process_url(self, path):
        url = list(urllib.parse.urlparse(path).path.split('/'))[1:]
        cid = None
        if url[0] == 'mupf' and len(url)>=2:
            cid = url[1]
            url = url[2:]
        url = tuple(url)
        return url, cid

    @staticmethod
    def _HTTP_error_response(status: HTTPStatus, reason: str):
        return(
            status,
            websockets.http.Headers(),
            f"{status.value} {status.name}\nReason: {reason}".encode('utf-8')
        )

    def _serve_static(self, path, type_, *, data_resolved=True):
        header = {}
        path = "static/"+path
        if type_ == 'html':
            header = {'Content-Type': f'text/html; charset={self._charset}',}
        elif type_ == 'js' or type_ == 'jsm':
            header = {'Content-Type': 'application/javascript',}
        if type_ == 'jsm':
            datastream = MacroByteStream(
                    pkg_resources.resource_stream(__name__, path),
                    substream_finder = lambda fname: pkg_resources.resource_stream(__name__, fname),
                    code_name = path,
                ).set_from_features(self._features)
        else:
            datastream = pkg_resources.resource_stream(__name__, path)
        if data_resolved:
            return (HTTPStatus.OK, websockets.http.Headers(header), datastream.read())
        else:
            return (HTTPStatus.OK, websockets.http.Headers(header), datastream)

    @loggable()
    def _identify_line_in_code(self, position_data):
        file_name, line, col = position_data
        if file_name.endswith('/mupf/core'):
            if position_data := self._serve_static('core-base.js', 'jsm', data_resolved=False)[2].identify_line(line):
                return (position_data[0], position_data[1], col)

    @loggable()
    def register_route(self, route: str, **kwargs) -> None:
        route, cid = self._process_url('/'+route)
        if cid is not None or route[0:1] == ('mupf',) or route == ('',):
            raise ValueError('route reserved')
        if 'file' in kwargs:
            self._file_routes[route] = kwargs['file']
        else:
            raise TypeError('route destination required')

    @loggable()
    def _get_route_response(self, route, cid):
        if route in self._file_routes:
            return (
                HTTPStatus.OK,
                websockets.http.Headers({
                    'Content-Type': mimetypes.guess_type(route[-1])[0],
                }),
                open(os.path.join(self._root_path, self._file_routes[route]), 'rb').read()   # TODO: check if exists
            )
        else:
            log_server_event('HTTP 404', route=route)
            return self._HTTP_error_response(HTTPStatus.NOT_FOUND, f"no route {route!r}")

#endregion

    @loggable()
    def piggyback_call(self, function, *args):
        self._event_loop.call_soon_threadsafe(function, *args)

    def __repr__(self):
        return f"<App {id(self):X}>"

#
# `_logging.py` hooks
#

@loggable('app.py/server_event', log_exit=False)
def log_server_event(*args, **kwargs):
    pass

@loggable('app.py/websocket_event', log_exit=False)
def log_websocket_event(*args, **kwargs):
    pass

loggable_class(websockets.server.WebSocketServer,
    long = lambda self: f"<WebSocket Server {id(self):X}>",
    long_det = lambda self: f"<obj of WebSocket Server>",
)

loggable_class(websockets.server.WebSocketServerProtocol,
    long = lambda self: f"<WebSocket Protocol {id(self):X}>",
    long_det = lambda self: f"<obj of WebSocket Protocol>",
)

def _eventloop_logger(evl):
    if evl.is_closed():
        return "<EventLoop closed>"
    if not evl.is_running():
        return "<EventLoop halted>"
    return "<EventLoop>"

loggable_class(asyncio.BaseEventLoop,
    long = _eventloop_logger,
    long_det= _eventloop_logger,
)

loggable_class(websockets.http.Headers,
    long = lambda self: f"<HTTP Header from {self['Host']}>",
    long_det = lambda self: f"<HTTP Header from {self['Host']}>",
)
