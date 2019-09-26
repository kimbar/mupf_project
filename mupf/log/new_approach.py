from . import _names as names
from . import _main as main
from . import _verbosity as verbosity

class LogManager:

    _managers_by_addr = {}
    
    def __init__(self, addr, log_path=True):
        self.log_path = log_path
        self._addr = None
        self.printed_addr = None
        self.addr = addr
        self._state = None
        self._writer_count = 0               # how many counts of this manager's function has been done
        self._writers = {}

    @property
    def addr(self):
        return self._addr

    @addr.setter
    def addr(self, value):
        self._addr = value
        if self.log_path:
            self.printed_addr = value
        else:
            self.printed_addr = names.build_path([names.parse_path(value)[-1]])

    def log_state_change(self, state):
        if self._addr == self.printed_addr:
            main.just_info('logging: {} {}'.format(state, self._addr))
        else:
            main.just_info('logging: {} {}     (as {})'.format(state, self._addr, self.printed_addr))

    def on(self):
        """ Turn on logging for this manager

        Calls already in progress won't be logged
        """
        if self._state != True:
            self.log_state_change('+')
        self._state = True

    def off(self):
        """ Turn off logging for this manager

        Calls already in progress will be logged
        """
        if self._state != False:
            self.log_state_change('-')
        self._state = False

    def add(self, auto_on=False):
        """ Add the manager to the registry
        """
        if self._addr in LogManager._managers_by_addr:
            main.just_info('ERROR: Adding `{}` manager failed - address already exists'.format(self._addr))
            return False
        LogManager._managers_by_addr[self._addr] = self
        if auto_on:
            if names.should_be_on(self._addr) == '+':
                self.on()
            else:
                self.off()
        return True

    def on_event(self, event):
        raise NotImplementedError('`LogManager.on_event()` not in `{}`'.format(self))

    def new_writer(self):
        id_ = self._writer_count
        self._writer_count += 1  # TODO: thread safeing
        wr = LogWriter(id_)
        self._writers[id_] = wr   # TODO: more sophisticated
        return wr

    def find_writer(self, id_):
        return self._writers[id_]


class LogSimpleManager(LogManager):

    _dangling_simple_managers = []

    def __init__(self, addr, log_path, func_parent, func_name):
        self.func_parent = func_parent              # the object (class or module) that holds the method/function/property
        self.func_name = func_name        # the name of the function that is wrapped
        
        self.sentinel = None               # the wrapper for function doing the actual logging
        self.property_name = None         # property name if the function is actually an accesor of property
        self.aunt_nicknames = {}

        super().__init__(addr, log_path)
        LogSimpleManager._dangling_simple_managers.append(self)
    
    def add(self, auto_on=False):
        if not super().add(auto_on):
            return False
        LogSimpleManager._dangling_simple_managers.remove(self)
        return True

    def set_as_property_manager(self, property_name):
        self.property_name = property_name

    def on(self):
        if self.property_name is None:
            self.sentinel = LogFunctionSentinel(self, self.func_parent, self.func_name)
        else:
            self.sentinel = LogPropertySentinel(self, self.func_parent, self.property_name, self.func_name)
        # If wrapped a sentinel, then unwrap the monad
        # this loop makes `on()` method idempotent
        while not self.sentinel.is_first_level:
            self.sentinel = self.sentinel._func
        super().on()

    def off(self):
        if self.sentinel is not None:
            self.sentinel.remove_yourself()
        self.sentinel = None
        super().off()

    def employ(self, aunt, nickname=None):
        self.aunt_nicknames[aunt] = nickname

    def dismiss(self, aunt):
        del self.aunt_nicknames[aunt]

    def on_event(self, event):
        if event.entering():
            wr = self.new_writer()
            event._call_id = wr.id_
            wr.write(", ".join([verbosity.enh_repr(a) for a in event.args]+[k+"="+verbosity.enh_repr(v) for k,v in event.kwargs.items()]))
        else:
            wr = self.find_writer(id_=event.call_id)
            wr.write(verbosity.enh_repr(event.result), finish=True)
        
        for aunt, nickname in self.aunt_nicknames.items():
            event._sentinel_nickname = nickname
            aunt.on_event(event)


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
        # self._verbosity_manager = None
        # self._call_number = None
        # self._obj_repr = ''
        # self.track = "?"

    def __call__(self, *args, **kwargs):
        ev = LogEvent(None, self._func, args, kwargs, None)
        self._manager.on_event(ev)

        result = self._func(*args, **kwargs)

        ev = LogEvent(ev.call_id, self._func, args, kwargs, result)
        self._manager.on_event(ev)
        return result

    def remove_yourself(self):
        raise NotImplementedError('`LogSentinel.remove_yourself()` not in `{}`'.format(self))


class LogFunctionSentinel(LogSentinel):
    
    def __init__(self, manager, func_parent, func_name):
        super().__init__(manager, func_parent, func_name, getattr(func_parent, func_name))
        if self.is_first_level:
            setattr(func_parent, func_name, self)

    def remove_yourself(self):
        setattr(self._func_parent, self._func_name, self._func)


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
            return super().__call__(*args, **kwargs)
        else:
            method_sentinel = LogSentinel(
                manager = self._manager,
                func_parent = self._func_parent,
                func_name = self._func_name,
                func = self._func.__get__(args[0], self._func_parent),
            )
            # method_sentinel._obj_repr = verbosity.enh_repr(args[0], short=True)
            # rerun itself (copy), but w/o first argument (self)
            return method_sentinel(*args[1:], **kwargs)


class LogEvent:

    def __init__(self, call_id, func, fargs, fkwargs, fresult):
        self._call_id = call_id
        self._func = func
        self._fargs = fargs
        self._fkwargs = fkwargs
        self._fresult = fresult
        self._sentinel_nickname = None

    def entering(self, sentinel_nickname=None):
        return self._call_id is None and (sentinel_nickname is None or self._sentinel_nickname == sentinel_nickname)

    def exiting(self, sentinel_nickname=None):
        return self._call_id is not None and (sentinel_nickname is None or self._sentinel_nickname == sentinel_nickname)

    @property
    def result(self):
        if self._call_id is not None:
            return self._fresult
        raise AttributeError('No `result` on enter event')

    @property
    def call_id(self):
        return self._call_id

class LogWriter:

    def __init__(self, id_):
        self.id_ = id_
    
    def write(self, text, finish=False):
        pass