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

class App:
    """
    Class for an app. Object represents a server and port, and a thread with an event-loop.
    
    There is a little reason to have more than one object of this class in the process, however there may be periods in
    process execution when GUI is not needed. Destruction of this object represents destruction of GUI. This feature
    would be inconvenient if the API of this class was present directly in the `mupf` package namespace.
    """
    
    default_port = 57107

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

        self._event_loop = None
        self._clients_by_cid = {}
        self._file_routes = {}
        self._server_thread = threading.Thread(target=self._server_thread_body, daemon=True, name="mupfapp-{}:{}".format(host, port))
        self._server_thread.start()

    def get_unique_client_id(self):
        return base64.urlsafe_b64encode(uuid.uuid4().bytes).decode('ascii').rstrip('=')

    def summon_client(self, frontend=client.WebBrowser):
        cid = self.get_unique_client_id()
        client = frontend(self, cid)
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
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)
        start_server = websockets.serve(
            ws_handler = self._websocket_request,
            host = self._host,
            port = self._port,
            process_request = self._process_HTTP_request,
        )
        self._event_loop.run_until_complete(start_server)
        self._event_loop.run_forever()
        print('Clean end of mupf thread')
        # TODO: If the thread is non-daemonic this line is printing, but with it two tasks from
        # module `websockets` are destroyed -- `WebSocketServerProtocol.handler()` and
        # `WebSocketCommonProtocol.close_connection()` This means that we need to cancel them
        # gently beforehand somehow.

    def close(self):
        for cl in self._clients_by_cid.values():
            cl.close(dont_wait=False)   # TODO: tu jednak `True` a potem zaczekać dopiero
        self._event_loop.stop()
        # TODO: we need to wait for stop (?), because next line errors:
        # self._event_loop.close()

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

    def register_route(self, route, **kwargs):
        route = tuple(urllib.parse.urlparse('/'+route).path.split('/'))
        if route[0:2] == ('', 'mupf') or route == ('', ''):
            raise ValueError('route reserved')
        if 'file' in kwargs:
            self._file_routes[route] = kwargs['file']
        else:
            raise TypeError('route destination required')

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
        print('{:.3f} ->'.format(time.time()-self._t0), raw_msg)
        msg = client.Client.decode_json(None, raw_msg)
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

            print('{:.3f} ->'.format(time.time()-self._t0), raw_msg)
            msg = the_client.decode_json(raw_msg)

            mode = msg[0]
            ccid = msg[1]
            # noun = msg[2]
            pyld = msg[3]

            if mode == 1:   # response for a cmd
                the_client.command.resolve_by_id_mupf(ccid, pyld['result'])
            elif mode == 5:
                pass     # it's a callback
            elif mode == 7:
                pass     # it's a notification
            else:
                pass

        # here we are after communication breakdown
        if break_reason == '*last*':
            the_client.command.resolve_all_mupf(exceptions.ClientClosedNormally())    # TODO: what if not only `*last*` sits here - they should receive a `TimeoutError`, because the `*last*` didn't close them
        else:
            the_client.command.resolve_all_mupf(exceptions.ClientClosedUnexpectedly(break_reason))
