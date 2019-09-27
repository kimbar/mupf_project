import inspect
import types

from . import _main as main
from . import _names as names
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

    @property
    def args(self):
        return self._fargs

    @property
    def kwargs(self):
        return self._fkwargs

class LogWriter:

    def __init__(self, id_):
        self.id_ = id_
    
    def write(self, text, finish=False):
        print(text, '' if finish else '...')


def loggable(
    log_addr='*',
    log_args=True,
    log_results=True,
    log_enter=True,
    log_exit=True,
    log_path=True,
    joined=False,
    short=None,
    long=None,

):
    """ All-purpose decorator/function for setting up logging for "loggables"

    It is used as a decorator for functions, methods, properties and classes (it must be used for
    classes which have decorated methods or else the methods will be "dangling"!). It is also used
    as a regular function for so-called outer classes (i.e. classes imported from other modules
    that still should have nice representation in logs).
    """


    def loggable_decorator(x):
        """ Actual decorator for "loggables"

        It decorates functions/methods/property accesors, but also classes with any of the above.
        """
        nonlocal log_addr
        # If it is a function or method
        if isinstance(x, types.FunctionType):
            # replace the wildcard `*` in the given name with the actual name of the function
            log_addr = log_addr.replace('*',  x.__name__.strip('_'), 1)
            if x.__qualname__ != x.__name__:
                # It is a method, so a manager is created that has parent temporarily set to `None`
                # it will be sorted out when the class will be decorated. It is also temporarily arrached to
                # `_methodtolog` property of the method. It hangs here until the class is decorated -- then all
                # the `_methodtolog` will be clean up. If not the logger id "dangling" -- that means that
                # the class of this method was not decorated as it should.
                x._methodtolog = LogSimpleManager(
                    addr = log_addr,
                    log_path = True,
                    func_parent = None,
                    func_name = x.__name__,
                )
            else:
                # standalone function, so module can be given for a parent
                lfm = LogSimpleManager(
                    addr = log_addr,
                    log_path = True,
                    func_parent = inspect.getmodule(x),
                    func_name = x.__name__,
                )
                # That's it for a function, so it can be added to the registry
                # lfm.add(auto_on=main._logging_enabled)
                lfm.add(auto_on=True)
        elif isinstance(x, classmethod):
            # if it is a class method, the manager is created similarily as for a method, only the name must be digged
            # a one step deeper
            log_addr = log_addr.replace('*',  x.__func__.__name__.strip('_'), 1)
            x._methodtolog = LogSimpleManager(
                addr = log_addr,
                log_path = True,
                func_parent = None,
                func_name = x.__func__.__name__,
            )
        elif isinstance(x, type):
            # Finally a class is decorated. Now we will hopefully collect all the managers that were temporarily 
            # attached to methods `_methodtolog` properties
            log_addr = log_addr.replace('*',  x.__name__.strip('_'), 1)
            for prop_name in dir(x):
                # for each member of the class we try...
                member = x.__getattribute__(x, prop_name)
                if isinstance(member, property):
                    # if it is an actual property we will have potentially three managers to sort out
                    members = ((member.fget, 'fget'), (member.fset, 'fset'), (member.fdel, 'fdel'))
                else:
                    # if it is a regular method we have just one manager
                    members = ((member, None),)
                for member, subname in members:
                    try:
                        # Now we just try to update the manager that is hanging in the function. If it is not 
                        # hanging there that means that we have something other than decorated method here
                        # end the exception occurs.
                        #
                        # The `log_path` value is really only meaningful in the class decorator, but it is needed
                        # in all method managers, hence it is copied here
                        member._methodtolog.log_path = log_path
                        # New name for the wrapper is created from the name given in the class decorator, and the name
                        # obtained when the method was decorated
                        member._methodtolog.addr = log_addr + '.' + member._methodtolog.addr
                        # the parent is finally known and can be assigned to the manager
                        member._methodtolog.func_parent = x
                        # if `subname` we are in a property
                        if subname:
                            # what was stored before in the manager as a name is in fact the name of property
                            # so it has to be rewriten
                            member._methodtolog.property_name = member._methodtolog.func_name
                            # Function name is now one of the accesor functions: `fget`, `fset` or `fdel`
                            member._methodtolog.func_name = subname
                        # The method is finnaly properly set up and can be added to the registry
                        member._methodtolog.add(auto_on=main._logging_enabled)
                        # This temporary member is no longer needed
                        del member._methodtolog
                    except Exception:
                        # It was not a decorated method (most of the time it is not), so we do nothing
                        pass
            # When we decorate a class we can assign a logging "repr"s here. One is "short" and one
            # is "long". For descriptin see docstring of `enh_repr` function.
            if short is not None:
                verbosity.short_class_repr[x] = short
            if long is not None:
                verbosity.long_class_repr[x] = long
        # After decoration we return the original method/function, so the class/module has exactly the
        # same structure as it would have it wasn't decorated at all. All the information needed is stored
        # in the managers now. When the logging is turned on, the wrappers are created, and module/class
        # is altered
        return x
    return loggable_decorator

