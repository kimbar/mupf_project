""" Code run in the server thread of the `App` (mostly)

Most of the code which is run in the separate "server" thread is moved to this module. It provides abstract classes
which are supposed to be inherited by `App`, `Client` and so on. It is only a code management trick - there is no reason
not to include all of this code directly into non-abstract classes. However, it is much more managable to keep most of
the "server" thread code in one place, even if it spans through many classes.

The `Client_SrvThrItf._websocket_communication()` method is the propper heart of this module.

"""

import asyncio
import websockets
from .log import loggable
import re
import threading
import abc
from http import HTTPStatus
from . import _remote
from . import exceptions


class _WSTT:
    """ Web Socket Task Type

    A helper class keeping names of tasks used in the websocket coroutine.
    """
    recieve_data ='recieve_data'
    consume_outqueue = 'consume_outqueue'
    send_data = 'send_data'

class _CrrcanMode:
    """ CRRCAN mode

    A helper class keeping magic numbers of CRRCAN protocol modes.
    """
    cmd = 0; res = 1; run = 2; clb = 5; ans = 6; ntf = 7

re_crrcan_start = re.compile(r'\s*\[\s*(\d+)\s*,\s*(-?\d+)\s*,')
""" A regexp matching proper begining of the CRRCAN message

The groups in the regexp allow for quick extracting of the `mode` and `ccid` of the message
"""

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
            # Here everything happens
            self._event_loop.run_forever()
            # This loop is broken in `App.close()`
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
        """ Finds a matching client for incoming websocket

        After finding the client the control is given to appropriate client method. When the client is done with the
        websocket the exception object is set as a result for all pending commands. The exception object may be of
        `exceptions.ClientClosedNormally` class. This is expected exception for the `*last*` command.

        """
        log_websocket_event('entering websocket request body', new_websocket, path=path)
        url, cid = self._process_url(path)
        log_websocket_event('websocket path information', new_websocket, cid=cid, url=url)
        if the_client := self._get_client_by_cid(cid):
            log_websocket_event('client found, passing websocket', new_websocket, cid=cid, client=the_client)

            # All client messaging happens here
            exit_exception = await the_client._websocket_communication(new_websocket)

            the_client.command.set_all_resolved_with_exception_mupf(exit_exception)

            # This is probabbly not stricly required, but all cancelled messages should be at least logged. At this
            # point no new incoming messages are possible, so no new callbacks will be created. However, old callbacks
            # can still be present in the client's queue. The execution of notification callbacks is local so they are
            # no problem. If a regular callback would be strated now it still would be processed to the end, and the
            # answer will be attempted to be sent, and will try to land in `the_client._outqueue`.
            #
            # There is maybe a brief moment between connection breakdown and full cleaning of the
            # `the_client.__pending_websocket_tasks` when new data can land on the `the_client._outqueue` and after all
            # some data can be there from before the connection breakdown. That's why it is cleaned here. Before `await`
            # above returns the `the_client._healthy_connection` is set to `False` and this coro executes as a single
            # block to the end. All new `the_client.__put_on_outqueue` will be run after that, so they will see
            # `the_client._healthy_connection == False` and the dropped messages are logged there.
            #
            # Finally, the sheduling of callbacks in `Client` will see `the_client._healthy_connection == False` and
            # further calls to callbacks will be dropped altogether in `CallbackTask.run()`.
            while not the_client._outqueue.empty():
                data = the_client._outqueue.get_nowait()
                log_websocket_event('cancelling data send', client=the_client, data=data)
            log_websocket_event('client done with websocket', new_websocket, client=the_client)
        else:
            # no such client!
            pass
        log_websocket_event('exiting websocket request body', new_websocket, path=path)

    @loggable(log_exit=False) # FIXME: temporary turned off because of the length of the output
    async def _process_HTTP_request(self, path, request_headers):
        """ Processing of regular GET requests

        """
        # This is a temporary solution just to make basics work it should be done in some more systemic way.
        # An error here is pretty catastrophic!!! The `mupf` itself hangs
        url, cid = self._process_url(path)
        if url == ('',):
            return self._serve_static('main.html', 'html')
        elif url == ('mupf', 'bootstrap'):
            client = self._clients_by_cid.get(cid, None)
            await client._pyside_ready
            # This future is resolved if the Py-side is ready for commands, and the first command can be sent. In fact
            # the `*first*` command is sent directly in the `bootstrap.js` file and the regular data message for this
            # command through the websocket is supressed.
            client.command('*first*')()
            return self._serve_static('bootstrap.js', 'js')
        elif url == ('mupf', 'core'):
            return self._serve_static('core-base.js', 'jsm')
        elif url == ('mupf', 'ws'):
            # Here the `_websocket_request()` is run by the `websockets` library
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
        self._outqueue: asyncio.Queue = None
        evl = self._get_eventloop()
        self._pyside_ready = evl.create_future()
        evl.call_soon_threadsafe(self.__init_srvthr)

    def __init_srvthr(self):
        """ The part of the `__init__` that must be run in the thread of the event loop

        After the code is run in the eventloop the `_pyside_ready` future is resolved and this can be seen in other
        coroutines. This means that the Python side of the client is properly initialized and the Python code can start
        to issue CRRCAN protocol messages, even if those messages won't hit the JS-side yet (because the connection with
        the browser is lagging behind.)
        """
        self._outqueue = asyncio.Queue()
        self._pyside_ready.set_result(None)
        log_server_event('client pyside ready', client=self)

    def __add_websocket_task(self, name, *, websocket=None, data=None):
        """ Helper method for cleaner creating of the event loop tasks

        """
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
        """ Main loop of the client communication

        The tasks required for communication are kept in `self.__pending_websocket_tasks`. Approprietly to the state of
        data queues task are created, consumed and resheduled. The results of this process in the rawest form possible
        is then processed by appropriate methods of other `*_SrvThrItf` classes. All further processing of this data is
        made in the non-abstract counerparts of the `*_SrvThrItf` classes in the main thread.

        """
        log_websocket_event('entering client websocket request body', client=self)
        self.__add_websocket_task(_WSTT.recieve_data, websocket=websocket)
        self.__add_websocket_task(_WSTT.consume_outqueue)
        log_websocket_event('websocket task pool initiated', client=self, out_queue_size=self._outqueue.qsize())

        exit_exception = None

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
                log_websocket_event(f'[task] `{task_name}`', client=self, cancelled=cancelled, exception=exception)
                if cancelled:
                    continue

                if exception:
                    for task in self.__pending_websocket_tasks:
                        sucess = task.cancel()
                        log_websocket_event(f'       `{task_name}`: canceling task', client=self, task_name=task.get_name(), sucess=sucess)
                    if isinstance(exception, websockets.exceptions.ConnectionClosedOK):
                        self._healthy_connection = False
                        if exception.reason == '*last*':
                            data = f'[{_CrrcanMode.res},{self.command._last_ccid},0,{{"result":null}}]'
                        else:
                            # This notification is needed to assure last run of `Client.run_one_callback_blocking()` The
                            # notification itself does nothing - it only unblocks the main thread.
                            data = f'[{_CrrcanMode.ntf},-1,"*close*",{{"kwargs":{{"code":{exception.code}}}}}]'
                            exit_exception = exceptions.ClientClosedUnexpectedly()
                        self.__crrcan_switchboard(data, task_name)
                    else:
                        log_websocket_event(f'       `{task_name}`: UNKNOWN EXCEPTION IN TASK', client=self, exception=exception)
                    continue

                if task_name == _WSTT.consume_outqueue:
                    data_list = task.result()
                    log_websocket_event(f'       `{task_name}`', client=self, msg_count=len(data_list))
                    for data in data_list:
                        # Translate each data taken from the outgoing queue into a sending task
                        self.__add_websocket_task(_WSTT.send_data, websocket=websocket, data=data)
                    # Recreate the outgoing queue consuming task
                    self.__add_websocket_task(_WSTT.consume_outqueue)

                elif task_name == _WSTT.send_data:
                    pass

                elif task_name == _WSTT.recieve_data:
                    self.__add_websocket_task(_WSTT.recieve_data, websocket=websocket)
                    data = task.result()
                    self.__crrcan_switchboard(data, task_name)

        log_websocket_event('exiting client websocket request body', client=self, exit_exc=exit_exception)
        if exit_exception is None:
            return exceptions.ClientClosedNormally()
        return exit_exception

    def __crrcan_switchboard(self, data, task_name):
        log_websocket_event(f'       `{task_name}`: crrcan', client=self, data=data)
        if match := re_crrcan_start.match(data):
            mode, ccid = map(int, match.groups())
            log_websocket_event(f'       `{task_name}`: crrcan', client=self, mode=mode, ccid=ccid)
            if mode == _CrrcanMode.res:
                self.command.set_resolved_mupf(ccid, data)
            elif mode == _CrrcanMode.clb or mode == _CrrcanMode.ntf:
                self._callback_queue.put(_remote.CallbackTask(self, mode, ccid, data))
            else:
                # This really should schedule some kind of error callback
                log_websocket_event(f'       `{task_name}`: ILLEGAL CRRCAN MODE `{mode!r}`', client=self, data=data)
        else:
            log_websocket_event(f'       `{task_name}`: BAD CRRCAN MESSAGE FORMAT', client=self, data=data)

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
        is not established or halted for some reason. The data from the queue is processed by `self.__consume_outqueue`
        coro. The data is put on the queue through `self.__put_on_outqueue`.

        """
        self._get_eventloop().call_soon_threadsafe(self.__put_on_outqueue, data)

    def __put_on_outqueue(self, data):
        if self._healthy_connection:
            self._outqueue.put_nowait(data)
        else:
            log_websocket_event(f'data dropped from sending', client=self, data=data)

    @abc.abstractmethod
    def _get_eventloop(self) -> asyncio.AbstractEventLoop:
        raise NotImplementedError('method `_get_eventloop` must be defined in the subclass')


class MetaCommand_SrvThrItf:

    def __init__(cls):
        cls._global_mutex = threading.RLock()
        """ This global mutex is required to read and alter `_unresolved` """
        cls._ccid_counter = 1
        # TODO: Does the counter need to be protected by th mutex?
        cls._unresolved = {}

    def set_resolved_mupf(cls, ccid, raw_data):
        """ Put raw result data on the command object and unlock its mutex
        """
        with cls._global_mutex:
            if ccid in cls._unresolved:
                log_websocket_event('resolving', ccid=ccid, raw=raw_data)
                cmd = cls._unresolved[ccid]
                cmd._raw_result = raw_data
                cmd._is_resolved.set()
                del cls._unresolved[ccid]
            else:
                raise RuntimeError(f'Response data `{raw_data!r}` from client, with no ccid={ccid} command waiting for resolution')

    def set_all_resolved_with_exception_mupf(cls, exc):
        unresolved = []
        with cls._global_mutex:
            for ccid, cmd in cls._unresolved.items():
                cmd._resolve(exc)
                unresolved.append(cmd)
            cls._unresolved.clear()
        for cmd in unresolved:
            cmd._is_resolved.set()
            log_websocket_event(f'resolving command with exception', cmd=cmd, cls=cls, exc=exc)

@loggable('app.py/websocket_event', log_exit=False)
def log_websocket_event(*args, **kwargs):
    pass

@loggable('app.py/server_event', log_exit=False)
def log_server_event(*args, **kwargs):
    pass