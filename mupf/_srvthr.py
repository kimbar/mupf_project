""" Code run in the server thread of the `App`
"""

import asyncio
import websockets
from .log import loggable
import re
import threading
import abc
from http import HTTPStatus
from ._remote import CallbackTask


class _WSTT:
    "Web Socket Task Type"

    recieve_data ='recieve_data'
    consume_outqueue = 'consume_outqueue'
    send_data = 'send_data'

class _CrrcanMode:
    cmd = 0; res = 1; run = 2; clb = 5; ans = 6; ntf = 7

re_crrcan_start = re.compile(r'\s*\[\s*(\d+)\s*,\s*(\d+)\s*,')

class App_SrvThrItf(abc.ABC):

    def __init__(self):
        # The main event loop of the App. However, if event-loop cannot be done this holds an offending exception
        self._event_loop: asyncio.BaseEventLoop = None
        self._server_opened_mutex = threading.Event()
        self._server_closed_mutex = threading.Event()

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

    async def _websocket_request(self, new_websocket, path):
        log_websocket_event('entering websocket request body', new_websocket, path=path)
        url, cid = self._process_url(path)
        log_websocket_event('websocket path information', new_websocket, cid=cid, url=url)
        if the_client := self._get_client_by_cid(cid):
            log_websocket_event('client found, passing websocket', new_websocket, cid=cid, client=the_client)
            await the_client._websocket_communication(new_websocket)
            log_websocket_event('client done with websocket', new_websocket, client=the_client)
        else:
            # no such client!
            pass
        log_websocket_event('exiting websocket request body', new_websocket, path=path)

    @loggable(log_exit=False) # FIXME: temporary turned off because of the length of the output
    async def _process_HTTP_request(self, path, request_headers):
        # This is a temporary solution just to make basics work it should be done in some more systemic way.
        # An error here is pretty catastrophic!!! The `mupf` itself hangs
        url, cid = self._process_url(path)
        if url == ('',):
            return self._serve_static('main.html', 'html')
        elif url == ('mupf', 'bootstrap'):
            client = self._clients_by_cid.get(cid, None)
            await client._pyside_ready
            client.command('*first*')()
            return self._serve_static('bootstrap.js', 'js')
        elif url == ('mupf', 'core'):
            return self._serve_static('core-base.js', 'jsm')
        elif url == ('mupf', 'ws'):
            return None
        elif url == ('mupf','closed'):
            return self._serve_static('closed.html', 'html')
        elif url[0:1] == ('mupf',):
            return self._HTTP_error_response(HTTPStatus.GONE, "all paths in `/mupf` are reserved for internal use")
        else:
            return self._get_route_response(url, cid)

    @abc.abstractmethod
    def _get_client_by_cid(self, cid):
        raise NotImplementedError('method `_get_client_by_cid` must be defined in the subclass')

    @abc.abstractmethod
    def _process_url(self, path):
        raise NotImplementedError('method `_process_url` must be defined in the subclass')

    @abc.abstractmethod
    def _serve_static(self, path, type_, *, data_resolved=True):
        raise NotImplementedError('method `_serve_static` must be defined in the subclass')

    @abc.abstractmethod
    def _get_route_response(self, route, cid):
        raise NotImplementedError('method `_get_route_response` must be defined in the subclass')

    @staticmethod
    @abc.abstractmethod
    def _HTTP_error_response(status: HTTPStatus, reason: str):
        raise NotImplementedError('method `_HTTP_error_response` must be defined in the subclass')


class Client_SrvThrItf(abc.ABC):

    def __init__(self):
        self.__pending_websocket_tasks = set()
        self._pyside_ready = threading.Event()
        self._outqueue: asyncio.Queue = None
        evl = self._get_eventloop()
        self._pyside_ready = evl.create_future()
        evl.call_soon_threadsafe(self.__init_srvthr)

    def __init_srvthr(self):
        """ The part of the `__init__` that must be run in the thread of the event loop
        """
        self._outqueue = asyncio.Queue()
        self._pyside_ready.set_result(None)
        log_server_event('client pyside ready', client=self)

    def __add_websocket_task(self, name, *, websocket=None, data=None):
        if name == _WSTT.recieve_data:
            coro = websocket.recv()
        elif name == _WSTT.consume_outqueue:
            coro = self.__consume_outqueue()
        elif name == _WSTT.send_data:
            if data is None:
                return
            coro = websocket.send(data)
        else:
            raise ValueError(f'No such websocket task `{name!r}`')
        self.__pending_websocket_tasks.add(asyncio.create_task(coro, name=name))

    async def _websocket_communication(self, websocket):
        log_websocket_event('entering client websocket request body', client=self)
        self.__add_websocket_task(_WSTT.recieve_data, websocket=websocket)
        self.__add_websocket_task(_WSTT.consume_outqueue)
        log_websocket_event('websocket task pool initiated', client=self, out_queue_size=self._outqueue.qsize())

        while True:
            if not self.__pending_websocket_tasks:
                log_websocket_event('websocket pending task set empty', client=self)
                break
            log_websocket_event('websocket going to sleep', client=self)
            (done, self.__pending_websocket_tasks) = await asyncio.wait(
                self.__pending_websocket_tasks,
                return_when=asyncio.FIRST_COMPLETED,
                )

            log_websocket_event(
                'websocket awake',
                client=self,
                done_task_count=len(done),
                pending_count=len(self.__pending_websocket_tasks),
                out_queue_size=self._outqueue.qsize()
            )
            while done:
                task: asyncio.Task = done.pop()
                task_name = task.get_name()
                cancelled = task.cancelled()
                exception = None
                if not cancelled:
                    exception = task.exception()
                log_websocket_event(f'processing a task `{task_name}`', client=self, cancelled=cancelled, exception=exception)
                if cancelled:
                    continue

                if task_name == _WSTT.consume_outqueue:
                    data_list = task.result()
                    log_websocket_event(f'                  `{task_name}`', client=self, msg_count=len(data_list))
                    for data in data_list:
                        # Translate each data taken from the outgoing queue into a sending task
                        self.__add_websocket_task(_WSTT.send_data, websocket=websocket, data=data)
                    # Recreate the outgoing queue consuming task
                    self.__add_websocket_task(_WSTT.consume_outqueue)

                elif task_name == _WSTT.send_data:
                    if exception:
                        log_websocket_event(f'EXCEPTION IN TASK `{task_name}`', client=self, exception=exception)
                        continue

                elif task_name == _WSTT.recieve_data:
                    if exception:
                        if isinstance(exception, websockets.exceptions.ConnectionClosedOK):
                            data = f'[1,{self.command._last_ccid},0,{{"result":null}}]'
                        else:
                            log_websocket_event(f'EXCEPTION IN TASK `{task_name}`', client=self, exception=exception)
                            continue
                    else:
                        self.__add_websocket_task(_WSTT.recieve_data, websocket=websocket)
                        data = task.result()
                    log_websocket_event(f'                  `{task_name}`', client=self, data=data)
                    if match := re_crrcan_start.match(data):
                        mode, ccid = map(int, match.groups())
                        log_websocket_event(f'                  `{task_name}`', client=self, mode=mode, ccid=ccid)

                        if mode == _CrrcanMode.res:
                            self.command.set_resolved_mupf(ccid, data)
                        elif mode == _CrrcanMode.clb:
                            self._callback_queue.put(CallbackTask(self, ccid, data))
                        elif mode == _CrrcanMode.ntf:
                            pass
                        else:
                            # This really should schedule some kind of error callback
                            log_websocket_event(f'ILLEGAL CRRCAN MODE `{mode!r}`', client=self, data=data)
                    else:
                        log_websocket_event(f'BAD CRRCAN MESSAGE FORMAT', client=self, data=data)

        log_websocket_event('exiting client websocket request body', client=self)


    def close(self):
        for task in self.__pending_websocket_tasks:
            sucess = task.cancel()
            log_websocket_event('canceling task', client=self, task_name=task.get_name(), sucess=sucess)

    async def __consume_outqueue(self):
        """ Empty the outgoing queue

        This coro waits for at least one message on the outgoing queue, but if there is more, it takes them all.
        """
        result = []
        result.append(await self._outqueue.get())
        while not self._outqueue.empty():
            result.append(self._outqueue.get_nowait())
        return result

    def _send(self, data: bytes):
        """ Puts data to send on the outgoing queue

        The data is put thread-safe on the `asyncio.Queue`, so any number of messages can be sent even if the connection
        is not established or halted for some reason.
        """
        self._get_eventloop().call_soon_threadsafe(lambda x: self._outqueue.put_nowait(x), data)

    @abc.abstractmethod
    def _get_eventloop(self) -> asyncio.AbstractEventLoop:
        raise NotImplementedError('method `_get_eventloop` must be defined in the subclass')


class MetaCommand_SrvThrItf:

    def __init__(cls):
        cls._global_mutex = threading.RLock()
        cls._unresolved = {}
        cls._resolved_in_advance = []
        cls._resolved_raw_data = {}

    def set_resolved_mupf(cls, ccid, raw_data):
        with cls._global_mutex:
            if ccid in cls._unresolved:
                log_websocket_event('resolving', ccid=ccid, raw=raw_data)
                cmd = cls._unresolved[ccid]
                cmd._raw_result = raw_data
                cmd._is_resolved.set()
                del cls._unresolved[ccid]
            else:
                raise RuntimeError(f'Response data `{raw_data!r}` from client, with no ccid={ccid} command waiting for resolution')



@loggable('app.py/websocket_event', log_exit=False)
def log_websocket_event(*args, **kwargs):
    pass

@loggable('app.py/server_event', log_exit=False)
def log_server_event(*args, **kwargs):
    pass