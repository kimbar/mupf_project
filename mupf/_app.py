from . import client
import base64
import uuid
import threading
import asyncio
import websockets
import json
import urllib
from http import HTTPStatus
import os
import pkg_resources
import mimetypes
import mupf.exceptions as exceptions
import time
from ._macro import MacroByteStream
from . import _features as F
from . import _enhjson as enhjson

from ._logging import loggable

@loggable('App')
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
        host='127.0.0.1',
        port=default_port,
        charset='utf-8',
        features = (),
    ):
        self._t0 = time.time()
        self._host = host
        self._port = port
        self._charset = charset

        self._server_opened_mutex = threading.Event()
        self._server_closed_mutex = threading.Event()

        # these semm to be just one kind of features (sans bootstrap ones)
        try:
            feat_type_check = any([not isinstance(f, F.__dict__['__Feature']) for f in features])
        except Exception:
            raise TypeError("`feature` argumnet of `App` must be a **container** of features")
        if feat_type_check:
            raise TypeError("all features must be of `mupf.F.__Feature` type")
        self._features = set(reversed(features))
        self._features.update(F.feature_list)
        self._features = set(filter(lambda f: f.state, self._features))

        self._event_loop = None    # if event-loop cannot be done this holds an offending exception
        self._clients_by_cid = {}
        self._file_routes = {}

    @loggable()
    def get_unique_client_id(self):
        while True:
            cid = base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=')
            if '-' not in cid[0:6]:
                for used_cid in self._clients_by_cid:
                    if cid[0:6] == used_cid[0:6]:
                        break
                else:
                    break
        return cid

    @loggable()
    def summon_client(self, frontend=client.WebBrowser, **kwargs):
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

    @loggable()
    def _server_thread_body(self):
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        start_server = websockets.serve(
            ws_handler = self._websocket_request,
            host = self._host,
            port = self._port,
            process_request = self._process_HTTP_request,
        )
        server = None
        try:
            server = self._event_loop.run_until_complete(start_server)
            self._server_opened_mutex.set()
            self._event_loop.run_forever()
        except OSError as err:
            self._event_loop = err
        finally:
            if server is None:
                self._server_opened_mutex.set()
            else:
                server.close()
                self._event_loop.run_until_complete(server.wait_closed())
                self._event_loop.close()
                log_event_loop_closed()
                self._server_closed_mutex.set()

    @loggable()
    def __enter__(self):
        if self.is_opened():
            return self._clients_by_cid[list(self._clients_by_cid.keys())[0]]
        else:
            self.open()
            if not self.is_opened():
                raise self._event_loop    # if event-loop is not opened this is an exception
            return self

    @loggable()
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @loggable()
    def open(self):
        self._server_thread = threading.Thread(
            target = self._server_thread_body,
            daemon = False,
            name = "mupfapp-{}:{}".format(self._host, self._port)
        )
        self._server_thread.start()
        self._server_opened_mutex.wait()
        return self

    @loggable()
    def open_with_client(self, frontend=client.WebBrowser, **kwargs):
        self.__enter__()
        self.summon_client(frontend, **kwargs)
        return self

    @loggable()
    def is_opened(self, get_culprit=False):
        if get_culprit:
            if self.is_opened():
                return None
            else:
                return self._event_loop # if event-loop is not opened this is an exception
        else:
            return isinstance(self._event_loop, asyncio.events.AbstractEventLoop)

    @loggable()
    def close(self, wait=False):
        for cl in self._clients_by_cid.values():
            cl.close(_dont_remove_from_app=True)
        self._clients_by_cid.clear()
        self._event_loop.call_soon_threadsafe(self._event_loop.stop)
        if wait:
            self._server_closed_mutex.wait()

    # @loggable() # FIXME: temprary turned off because of the length of the output
    def _process_HTTP_request(self, path, request_headers):
        url = tuple(urllib.parse.urlparse(path).path.split('/'))
        if url == ('', ''):
            return (
                HTTPStatus.OK,
                websockets.http.Headers({
                    'Content-Type':'text/html; charset={0}'.format(self._charset),
                }),
                pkg_resources.resource_stream(__name__, "static/main.html").read()
            )
        elif url == ('', 'mupf', 'bootstrap'):
            return (
                HTTPStatus.OK,
                websockets.http.Headers({
                    'Content-Type':'application/javascript',
                }),
                pkg_resources.resource_stream(__name__, "static/bootstrap.js").read()
            )
        elif url == ('', 'mupf', 'core'):
            return (
                HTTPStatus.OK,
                websockets.http.Headers({
                    'Content-Type':'application/javascript',
                }),
                MacroByteStream(
                    pkg_resources.resource_stream(__name__, "static/core-base.js")
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
    def register_route(self, route, **kwargs):
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
                open(self._file_routes[route], 'rb').read()   # TODO: check if exists
            )
        else:
            pass  # 404

    async def _websocket_request(self, new_websocket, path):
        raw_msg = await new_websocket.recv()
        # print('{:.3f} ->'.format(time.time()-self._t0), raw_msg)
        msg = client.Client.decode_json_simple(raw_msg)
        result = msg[3]['result']
        cid = result['cid']
        the_client = self._clients_by_cid[cid]
        the_client._websocket = new_websocket
        the_client._user_agent = result['ua']
        
        # this line accepts a response from  `command('*first*')` because if the websocket is
        # open then the `*first` have been just executed
        the_client.command.resolve_by_id_mupf(ccid=0, result=None)
        the_client.await_connection()
        break_reason = None
        while True:
            try:
                raw_msg = await new_websocket.recv()
            except websockets.exceptions.ConnectionClosed as e:
                break_reason = e.reason
                break

            # print('{:.3f} ->'.format(time.time()-self._t0), raw_msg)
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

        # here we are after communication breakdown
        the_client._healthy_connection = False
        if break_reason == '*last*':
            the_client.command.resolve_all_mupf(exceptions.ClientClosedNormally())    # TODO: what if not only `*last*` sits here - they should receive a `TimeoutError`, because the `*last*` didn't close them
        else:
            the_client.command.resolve_all_mupf(exceptions.ClientClosedUnexpectedly(break_reason))

        log_websocket_request_end()
    
    @loggable()
    def piggyback_call(self, function, *args):
        self._event_loop.call_soon_threadsafe(function, *args)

    def __repr__(self):
        return "<App>"

@loggable()
def log_websocket_request_end():
    pass

@loggable()
def log_event_loop_closed():
    pass
