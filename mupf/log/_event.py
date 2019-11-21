import inspect

class LogEvent:

    def __init__(self, call_id, sentinel, func, fargs, fkwargs, fresult, thread, stack):
        self._call_id = call_id
        self._entering = (call_id is None)
        self._sentinel = sentinel
        self._func = func
        self._fargs = fargs
        self._fkwargs = fkwargs
        self._fresult = fresult
        self._thread = thread
        self._sentinel_nickname = None
        self._bound_arguments = None
        self._stack = stack

    def entering(self, sentinel_nickname=None):
        return self._entering and (sentinel_nickname is None or self._sentinel_nickname == sentinel_nickname)

    def exiting(self, sentinel_nickname=None):
        return not self._entering and (sentinel_nickname is None or self._sentinel_nickname == sentinel_nickname)

    @property
    def result(self):
        if self._call_id is not None:
            return self._fresult
        raise AttributeError('No `result` on enter event')

    @property
    def call_id(self):
        return self._call_id

    @property
    def args(self):
        return self._fargs

    @property
    def kwargs(self):
        return self._fkwargs

    @property
    def sentinel(self):
        return self._sentinel

    @property
    def thread(self):
        return self._thread

    @property
    def thread_name(self):
        return self._thread.name

    def arg(self, name):
        if self._bound_arguments is None:
            sig = inspect.signature(self._func)
            self._bound_arguments = sig.bind(*self._fargs, **self._fkwargs)
            self._bound_arguments.apply_defaults()
        return self._bound_arguments.arguments[name]
