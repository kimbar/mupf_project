import weakref
import threading
import time
from ._remote import RemoteObj
from .log import loggable

class MetaCommand(type):
    """
    Class of all commands. Object represents all possible commands for a specific client. Object is a class.

    Due to syntactic reasons, all possible commands for a single client are classes. For each client a class is made.
    Specific commands (by specific we mean when the name of a command is known) are instances of these classes.
    Therefore, all commands for all clients should also have a class. This is this class.

    This class provides an API to act on all commands for a given client, such as accessing a specific command by the
    property syntax. That means that if `X` is an object of `MetaCommand` class, the `X` is a class representing all
    possible commands for a specific client. The `X("go")` is an instance of `X` and represents a apecific command
    (named "go") for a specific client, and `X("go")(arg)` will issue this command with an argument `arg`.

    The `X.go` also represents the command "go" and `X.go(arg)` its execution, but with much convienient syntax. Normaly
    this syntax can be implemented as a class property. However, the names of all commands for a given client are not
    known in advance and can be even dynamically changed. The only solution is to resort to `__getattr__` method. It
    works fine for an object, but here we want it to act for the class `X`, not its instance. Therefore a metaclass is
    needed. Its `__getattr__` is called when the `X.go` is approached, and it simply invokes constructor `X("go")`.
    """

    def __init__(cls, name, bases, dict_):
        super().__init__(name, bases, dict_)
        cls._global_mutex = threading.RLock()
        cls._unresolved = {}
        cls._resolved_in_advance = []

    def __getattr__(cls, name: str):
        if name.endswith('mupf'):
            # In principle this could be done like in `RemoteObj`, but that'd require full `__getattribute__` spiel,
            # which may be a little too complicated for such a low-level stuff as naming commands. After all, this is
            # the main purpose of the "mupf" name - to name reserved things internally.
            raise RuntimeError('Command names cannot end with `mupf`')
        return cls(name)    #pylint: disable=no-value-for-parameter

    def resolve_all_mupf(cls, result):
        unres = []
        with cls._global_mutex:
            for ccid in cls._unresolved.keys():
                unres.append(cls._unresolved[ccid])
                if unres[-1]._is_resolved.is_set():
                    raise RuntimeError("Command already resolved")
            for cmd in unres:
                cmd._is_error = isinstance(result, Exception)
                cmd._result = result
            cls._unresolved.clear()
            for cmd in unres:
                cmd._is_resolved.set()

    def await_all_mupf(command_cls):
        pass

    def resolve_by_id_mupf(cls, ccid, result):
        with cls._global_mutex:
            if (ccid not in cls._unresolved):  #pylint: disable=no-value-for-parameter # this should be compared with `cls._ccid_counter`
                if result is not None:
                    raise RuntimeError("only `None` result allowed for commands from the future")
                cls._resolved_in_advance.append(ccid)
            else:
                cls._unresolved[ccid].result = result


@loggable('command.py/*')
def create_command_class_for_client(client):
    """
    Return a class "binded" to the `client`.
    """

    @loggable(
        f'command.py/*<{client._cid[0:6]}><obj>',
        log_path = False,
        short = lambda self: f"<{getattr(self, '_ccid', '?')}-{id(self):X}>",
        long = lambda self: f"<Command {('run' if getattr(self, '_notification', False) else 'cmd')} {getattr(self, '_ccid', '?')} {getattr(self, '_cmd_name', '?')} {id(self):X}>",
        short_det = lambda self: f"<{getattr(self, '_ccid', '?')}>",
        long_det = lambda self: f"<Command {('run' if getattr(self, '_notification', False) else 'cmd')} {getattr(self, '_ccid', '?')} {getattr(self, '_cmd_name', '?')}>",
    )
    class Command(metaclass=MetaCommand):
        """
        Class of all possible commands for a specific client. Object represents a specific (named) command.

        For details of the class structure see description of `MetaCommand`.

        The object is a callable. Its call executes the command. The `result` property holds the result of the command,
        however if it is attempted to read the `result` when it is not already known, the current thread will be blocked
        until the result is known. If an error occured during execution, attempt to read the `result` will rise an
        appropriate exception.
        """
        # This should end in `_mupf`? Because they can be confused with command names
        _client_wr = weakref.ref(client)
        # _unresolved = {}
        # _resolved_in_advance = []
        # _global_mutex = threading.RLock()
        _ccid_counter = 0
        _legal_names = ['*first*', '*last*', '*install*', '*features*']

        @loggable(log_results=False)
        def __init__(self, cmd_name, notification=False):
            self._ccid = None
            self._cmd_name = cmd_name
            self._notification = notification
            self._is_resolved = threading.Event()
            self._result = None
            self._is_error = False

        @loggable('()')
        def __call__(self, *args, **kwargs):
            # TODO: notifications can be send multiple times and commands only once!
            if self._cmd_name not in Command._legal_names:
                # print(f'*** Warning, there is no `{self._cmd_name}` command ***')
                pass
            if self._is_resolved.is_set():
                self._result = None
                self._is_error = False
                self._is_resolved.clear()
            with Command._global_mutex:
                if Command._ccid_counter < 0:
                    raise RuntimeError(f'`*last*` command was already sent, trying to send `{self._cmd_name}`(args={args}, kwargs={kwargs})')
                if self._ccid in Command._unresolved:
                    raise RuntimeError('reissue impossible right now')
                self._ccid = Command._ccid_counter
                if self._notification:
                    self._is_resolved.set()
                else:
                    Command._unresolved[self._ccid] = self
                if self._cmd_name != '*last*':
                    Command._ccid_counter += 1
                else:
                    Command._ccid_counter = -1
            j = self._jsonify(args, kwargs)
            # print(f'<- {time.time()-self._client_wr().app._t0:.3f}', j)
            if self._ccid > 0:    # `cmd_name=="__first__"` cannot be send, only received
                Command._client_wr().send_json(j)
            if self._ccid in Command._resolved_in_advance:
                with Command._global_mutex:
                    self.result = None
                    del Command._resolved_in_advance[self._ccid]
            return self

        @loggable()
        def run(self, *args, **kwargs):
            ntf = self._notification
            self._notification = True
            self(*args, **kwargs)
            self._notification = ntf
            return self

        # client.command.print.notification('no result value')

        @loggable()
        def _jsonify(self, args, kwargs):
            return [
                (2 if self._notification else 0),   # Magic numbers: mode
                self._ccid,
                self._cmd_name,
                {
                    'args': args,
                    'kwargs': kwargs,
                },
            ]

        @property
        @loggable()
        def wait(self):
            self._is_resolved.wait()
            return self

        @property
        @loggable('*.:')
        def result(self):
            self.wait
            if self._is_error:
                raise self._result
            return self._result

        @result.setter
        @loggable('*.=', log_results=False)
        def result(self, result):
            if self._notification:
                raise RuntimeError('cannot resolve notification')
            with Command._global_mutex:
                if self._is_resolved.is_set():
                    raise RuntimeError("command already resolved")
                if isinstance(result, RemoteObj):
                    self._is_error = False
                else:
                    self._is_error = isinstance(result, Exception)
                self._result = result
                del Command._unresolved[self._ccid]
                self._is_resolved.set()

        @loggable()
        def is_in_bad_state(self):
            if not self._is_resolved.is_set():
                return True
            if self._is_error:
                return self._result
            return False

    return Command
