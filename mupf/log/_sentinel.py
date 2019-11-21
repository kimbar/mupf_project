import copy
import threading
import inspect

from . import _address as address
from . import _writer as writer
from ._event import LogEvent
from . import settings


class LogSentinel:

    def __init__(self, manager, func_parent, func_name, func):
        if isinstance(func, LogSentinel):
            self.is_first_level = False
            return
        self.is_first_level = True
        self._func = func
        self._manager = manager
        self._func_parent = func_parent
        self._func_name = func_name
        self._printed_addr = address.build_path(self._manager.printed_addr_tree)

    def __call__(self, *args, **kwargs):
        stack = None
        if settings.graph_call_stack_connect:
            stack = inspect.stack()
        ev = LogEvent(None, self, self._func, args, kwargs, None, threading.current_thread(), stack)
        self._manager.on_event(ev)
        call_id = ev.call_id
        del ev
        if stack is not None:
            del stack

        result = self._func(*args, **kwargs)

        ev = LogEvent(call_id, self, self._func, args, kwargs, result, threading.current_thread(), None)
        self._manager.on_event(ev)
        return result

    def remove_yourself(self):
        raise NotImplementedError('`LogSentinel.remove_yourself()` not in `{}`'.format(self))

    def copy(self):
        # Here some registration of a copy can be made in the manager
        # but for now it seems not to be needed
        return LogSentinel(
            manager = self._manager,
            func_parent = self._func_parent,
            func_name = self._func_name,
            func = self._func,
        )


class LogFunctionSentinel(LogSentinel):

    def __init__(self, manager, func_parent, func_name):
        super().__init__(manager, func_parent, func_name, getattr(func_parent, func_name))
        if self.is_first_level:
            setattr(func_parent, func_name, self)

    def remove_yourself(self):
        setattr(self._func_parent, self._func_name, self._func)

    def __get__(self, obj, class_):
        method_sentinel = self.copy()
        method_sentinel._func = self._func.__get__(obj, class_)
        if obj is not None:
            method_sentinel._printed_addr = address.build_path(self._manager.printed_addr_tree, dict(obj=writer.enh_repr(obj, short=True)))
        return method_sentinel


class LogPropertySentinel(LogSentinel):

    def __init__(self, manager, class_, property_name, accessor_name):
        super().__init__(manager, class_, accessor_name, getattr(class_.__getattribute__(class_, property_name), accessor_name))
        self._property_name = property_name
        if self.is_first_level:
            property_ = class_.__getattribute__(class_, self._property_name)
            property_decorator_name = {'fget':'getter', 'fset':'setter', 'fdel': 'deleter'}[accessor_name]
            setattr(class_, self._property_name, getattr(property_, property_decorator_name)(self))

    def remove_yourself(self):
        class_ = self._func_parent
        property_ = class_.__getattribute__(class_, self._property_name)
        # This is a remnant form another algorithm where number of wrapped accessors was
        # monitored and when all were unwrapped a `True` was emmited from this method
        # Now it is simplified, but this is left for future refactorization
        num = ['fget', 'fset', 'fdel'].index(self._func_name)
        is_wrapped = list(map(lambda x: isinstance(x, LogSentinel), [property_.fget, property_.fset, property_.fdel]))
        if is_wrapped[num]:
            decor_name = ['getter', 'setter', 'deleter'][num]
            setattr(class_, self._property_name, getattr(property_, decor_name)(self._func))

    def __call__(self, *args, **kwargs):
        if hasattr(self._func, '__self__'):
            # This is probably inaccessible, because the function is always wrapped in
            # the `LogSentinel` below?
            # It is a remnant from the old approach where `__call__` was a general
            # entry point for a sentinel, now it is separated by `LogPropertySentinel` vs `LogFunctionSentinel`
            return super().__call__(*args, **kwargs)
        else:
            method_sentinel = self.copy()
            method_sentinel._func = self._func.__get__(args[0], self._func_parent)
            method_sentinel._printed_addr = address.build_path(self._manager.printed_addr_tree, dict(obj=writer.enh_repr(args[0], short=True)))
            # rerun itself (copy), but w/o first argument (self)
            return method_sentinel(*args[1:], **kwargs)
