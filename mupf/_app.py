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
from .log import loggable


@loggable(
    'app.py/*<obj>',
    log_path = False,
    short = lambda self: f"<{id(self):X}>",
    long = lambda self: f"<App {id(self):X}>",
)
class App:
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

        self._server_opened_mutex = threading.Event()
        self._server_closed_mutex = threading.Event()

        # Checking the format of `features` argument.
        # Tested in `vanilla_env/test_featyres.py/Features`
        try:
            feat_type_check = any([not isinstance(f, F.__dict__['__Feature']) for f in features])
        except Exception:
            raise TypeError("`feature` argumnet of `App` must be a **container** of features")
        if feat_type_check:
            raise TypeError("all features must be of `mupf.F.__Feature` type")

        # Features are added in reverse order than listed in `features`,
        # because of the semantics of `set()` creator - doing nothing when an
        # element already exists. The features are hashed by their names only
        # (not name and state) This way stored state of a feature is taken from
        # the last occurence of a given feature on the list.
        self._features = set(reversed(features))
        # `.update()` has the same semantics as creator, so only features not
        # on the list are added (with their default states).
        self._features.update(F.feature_list)
        self._features = set(filter(lambda f: f.state, self._features))

        # The main event loop of the App. However, if event-loop cannot be done
        # this holds an offending exception
        self._event_loop: asyncio.BaseEventLoop = None
        self._clients_by_cid: dict[str, client.Client] = {}
        self._root_path: str = os.path.split(sys.argv[0])[0]
        self._file_routes: dict[str, str] = {}

        self._clients_generated = 0

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
        cid = self.get_unique_client_id()
        client = frontend(self, cid, **kwargs)
        self._clients_by_cid[cid] = client
        client.install_javascript(src='mupf/core').result
        for feat, state in client.command('*features*')().result.items():
            if state:
                client.features.add(+getattr(F, feat))
        if F.core_features in client.features:
            client.command._legal_names.append('*getcmds*')
            client.command._legal_names = client.command('*getcmds*')().result
        client.summoned()
        return client

    def _server_thread_body(self):
        """ Main body of the server, run in a separate thread in `self.open()`
        """
        log_server_event('entering server thread body')
        self._event_loop = asyncio.new_event_loop()
        log_server_event('creating event loop', eloop=self._event_loop)
        asyncio.set_event_loop(self._event_loop)
        log_server_event('creating server object')
        start_server = websockets.serve(
            ws_handler = self._websocket_request,
            host = self._host,
            port = self._port,
            process_request = self._process_HTTP_request,
        )
        server = None
        try:
            log_server_event('server starting ...')
            server = self._event_loop.run_until_complete(start_server)
            log_server_event('server started', server)
            self._server_opened_mutex.set()
            log_server_event('server open state mutex set', server)
            self._event_loop.run_forever()
            # Here everything happens
            log_server_event('event loop main run ended', server, eloop=self._event_loop)
        except OSError as err:
            log_server_event('server OSError', err, server)
            self._event_loop = err
        finally:
            if server is None:
                self._server_opened_mutex.set()
                log_server_event('server open state mutex set', server)
            else:
                log_server_event('server closing ...', server)
                server.close()
                log_server_event('server closed', server)
                self._event_loop.run_until_complete(server.wait_closed())
                log_server_event('event loop completed', server, eloop=self._event_loop)
                self._event_loop.close()
                log_server_event('event loop closed', server, eloop=self._event_loop)
                self._server_closed_mutex.set()
                log_server_event('server close state mutex set', server)
        log_server_event('exiting server thread body', server)

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

        It returns `False` if it is not closed. Otherwise it returns `True` by
        default or an exception if asked for the culprit of the app being
        closed. The exception is not rised - it is only returned and must be
        rised outside.
        """
        if get_culprit:
            if not self.is_closed():
                return False
            elif isinstance(self._event_loop, asyncio.events.AbstractEventLoop):
                return RuntimeError(f'Event loop in `{self}` was closed')
            elif self._event_loop is None:
                # It's hard to give a reason, because this should never happen
                # (FLW) unless user creates App, does not open it and asks why
                # it is closed.
                return RuntimeError(f'Event loop in `{self}` was never created (`App` was never opened?)')
            else:
                return self._event_loop # if event-loop is not opened this is an exception
        else:
            if isinstance(self._event_loop, asyncio.events.AbstractEventLoop):
                return self._event_loop.is_closed()
            else:
                return True

    @loggable()
    def close(self, wait=False):
        for cl in self._clients_by_cid.values():
            cl.close(_dont_remove_from_app=True)
        self._clients_by_cid.clear()
        self._event_loop.call_soon_threadsafe(self._event_loop.stop)
        if wait:
            self._server_closed_mutex.wait()

#region It's a mess

    # The serving of so-called static files become quite a mess. It is because
    # this subsystem was never really designed as a whole. Right now it
    # consists of following parts:
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

    @loggable(log_results=False) # FIXME: temporary turned off because of the length of the output
    def _process_HTTP_request(self, path, request_headers):
        # This is a temporary solution just to make basics work
        # it should be done in some more systemic way.

        # An error here is pretty catastrophic!!! The `mupf` itself hangs

        cid = request_headers.get('Cookie', None)    # This can now be used to set `Client` features to `core.js`
        url = tuple(urllib.parse.urlparse(path).path.split('/'))

        if url == ('', ''):
            return (
                HTTPStatus.OK,
                websockets.http.Headers({
                    'Content-Type': f'text/html; charset={self._charset}',
                }),
                pkg_resources.resource_stream(__name__, "static/main.html").read()
            )
        elif url == ('', 'mupf', 'bootstrap'):
            return (
                HTTPStatus.OK,
                websockets.http.Headers({
                    'Content-Type': 'application/javascript',
                }),
                pkg_resources.resource_stream(__name__, "static/bootstrap.js").read()
            )
        elif url == ('', 'mupf', 'core'):
            return (
                HTTPStatus.OK,
                websockets.http.Headers({
                    'Content-Type': 'application/javascript',
                }),
                MacroByteStream(
                    pkg_resources.resource_stream(__name__, "static/core-base.js"),
                    substream_finder = lambda fname: pkg_resources.resource_stream(__name__, fname),
                    code_name = "static/core-base.js",
                ).set_from_features(self._features).read()
            )
        elif url == ('', 'mupf', 'ws'):
            return None
        elif url[0:2] == ('', 'mupf') :
            return (
                HTTPStatus.GONE,
                websockets.http.Headers(),
                b"410 GONE\nReason: all paths in `/mupf` are reserved for internal use",
            )
        else:
            return self._get_route_response(url)

    @loggable()
    def _identify_line_in_code(self, position_data):
        file_name, line, col = position_data
        if file_name.endswith('/mupf/core'):
            if position_data := MacroByteStream(
                    pkg_resources.resource_stream(__name__, "static/core-base.js"),
                    substream_finder = lambda fname: pkg_resources.resource_stream(__name__, fname),
                    code_name = "static/core-base.js",
                ).set_from_features(self._features).identify_line(line):
                return (position_data[0], position_data[1], col)

    @loggable()
    def register_route(self, route: str, **kwargs) -> None:
        route = tuple(urllib.parse.urlparse('/'+route).path.split('/'))
        if route[0:2] == ('', 'mupf') or route == ('', ''):
            raise ValueError('route reserved')
        if 'file' in kwargs:
            self._file_routes[route] = kwargs['file']
        else:
            raise TypeError('route destination required')

    @loggable()
    def _get_route_response(self, route):
        if route in self._file_routes:
            return (
                HTTPStatus.OK,
                websockets.http.Headers({
                    'Content-Type': mimetypes.guess_type(route[-1])[0],
                }),
                open(os.path.join(self._root_path, self._file_routes[route]), 'rb').read()   # TODO: check if exists
            )
        else:
            log_server_event('HTTP Status 404', route=route)
            pass

#endregion

    async def _websocket_request(self, new_websocket, path):
        log_websocket_event('entering websocket request body', new_websocket, path=path)
        raw_msg = await new_websocket.recv()
        log_websocket_event('websocket received result of *first*', new_websocket, msg=raw_msg)
        msg = client.Client.decode_json_simple(raw_msg)
        result = msg[3]['result']
        cid = result['cid']
        the_client = self._clients_by_cid[cid]
        the_client._websocket = new_websocket
        log_websocket_event('websocket assigned to client', new_websocket, client=the_client)
        the_client._user_agent = result['ua']

        # this line accepts a response from  `command('*first*')` because if the websocket is
        # open then the `*first` have been just executed
        the_client.command.resolve_by_id_mupf(ccid=0, result=None)
        log_websocket_event('websocket awaiting for client...', new_websocket, client=the_client)
        the_client.await_connection()
        log_websocket_event('websocket contacted by client', new_websocket, client=the_client)
        break_reason = None
        while True:
            log_websocket_event('websocket going to sleep', new_websocket)
            try:
                raw_msg = await new_websocket.recv()
            except websockets.exceptions.ConnectionClosed as e:
                break_reason = e.reason
                break

            # print(f'{time.time()-self._t0:.3f} ->', raw_msg)
            msg = the_client.decode_json(raw_msg)

            mode = msg[0]
            ccid = msg[1]
            noun = msg[2]
            pyld = msg[3]

            if mode == 1:   # response for a cmd
                the_client.command.resolve_by_id_mupf(ccid, pyld['result'])
            elif mode == 5:
                the_client.shedule_callback(ccid, noun, pyld)
            elif mode == 7:
                the_client.shedule_callback(ccid, noun, pyld)
                if noun == '*close*':
                    break_reason = noun
                    break
            else:
                pass

        log_websocket_event('websocket communication breakdown', new_websocket, break_reason=break_reason)
        # here we are after communication breakdown
        the_client._healthy_connection = False
        if break_reason == '*last*':
            the_client.command.resolve_all_mupf(exceptions.ClientClosedNormally())    # TODO: what if not only `*last*` sits here - they should receive a `TimeoutError`, because the `*last*` didn't close them
        else:
            the_client.command.resolve_all_mupf(exceptions.ClientClosedUnexpectedly(break_reason))

        log_websocket_event('exiting websocket request body', new_websocket)

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

loggable(
    outer_class = websockets.server.WebSocketServer,
    long = lambda self: f"<WebSocket Server {id(self):X}>",
)

loggable(
    outer_class = websockets.server.WebSocketServerProtocol,
    long = lambda self: f"<WebSocket Protocol {id(self):X}>",
)

def _eventloop_logger(evl):
    if evl.is_closed():
        return "<EventLoop closed>"
    if not evl.is_running():
        return "<EventLoop halted>"
    return "<EventLoop>"

loggable(
    outer_class = asyncio.selector_events.BaseSelectorEventLoop,
    long = _eventloop_logger,
)

loggable(
    outer_class = websockets.http.Headers,
    long = lambda self: f"<HTTP Header from {self['Host']}>",
)
