from . import _address as address
from . import _main as main
from . import _writer as writer
from ._sentinel import LogFunctionSentinel, LogPropertySentinel


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
            self.printed_addr = address.build_path([address.parse_path(value)[-1]])

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
            if address.should_be_on(self._addr) == '+':
                self.on()
            else:
                self.off()
        return True

    def on_event(self, event):
        raise NotImplementedError('`LogManager.on_event()` not in `{}`'.format(self))

    def new_writer(self, style):
        id_ = self._writer_count
        self._writer_count += 1  # TODO: thread safeing
        wr = writer.LogWriter(id_, self._addr, style)
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
            wr = self.new_writer(writer.LogWriterStyle.inner)
            event._call_id = wr.id_
            wr.write(", ".join([writer.enh_repr(a) for a in event.args]+[k+"="+writer.enh_repr(v) for k,v in event.kwargs.items()]))
        else:
            wr = self.find_writer(id_=event.call_id)
            wr.write(writer.enh_repr(event.result), finish=True)
        
        for aunt, nickname in self.aunt_nicknames.items():
            event._sentinel_nickname = nickname
            aunt.on_event(event)


def refresh():
    for l in LogManager._managers_by_addr.values():
        if address.should_be_on(l.addr) == '+':
            l.on()
        else:
            l.off()

# class LoggableFuncManager:
#     """ Object represents a POSIBILITY of logging of a function/method/property

#     The logging is turned on by `LoggableFuncManager.on()`
#     """
#     _loggables_by_name = {}
#     _dangling_loggables = []

#     def __init__(self, name, parent, func_name, verbosity_manager):
#         if name in LoggableFuncManager._loggables_by_name:
#             raise ValueError('Loggable name `{}` already exists'.format(name))
#         self.parent = parent              # the object (class or module) that holds the method/function/property
#         self.func_name = func_name        # the name of the function that is wrapped
#         self.verbosity_manager = verbosity_manager
#         self._name = None                 # the name of manager (accesed by property)
#         self.printed_name = None          # the name of manager actually printed in the log
#         self.wrapper = None               # the wrapper for function doing the actual logging
#         self.call_count = 0               # how many counts of this manager's function has been done
#         self.property_name = None         # property name if the function is actually an accesor of property
#         # self.log_path = log_path          # should the "path" part of the name be logged in the output
#         # self.log_args = log_args          # should the args of a call be logged
#         # self.log_results = log_results    # should the results of a call be logged
#         # self.log_enter = log_enter        # should the call begining be logged
#         # self.log_exit = log_exit          # should the call ending be logged
#         # self.joined = joined              # is it a `joined` version of logging graph

#         # tidy up the `name` and `printed_name` things
#         self.name = name
#         # The manager is dangling until added to the registry
#         LoggableFuncManager._dangling_loggables.append(self)

#     @property
#     def name(self):
#         return self._name

#     @name.setter
#     def name(self, value):
#         self._name = value
#         if self.verbosity_manager._log_path:
#             self.printed_name = value
#         else:
#             self.printed_name = names.build_path([names.parse_path(value)[-1]])

#     def add(self, on=False):
#         """ Add the manager to the registry
#         """
#         if self.name in LoggableFuncManager._loggables_by_name:
#             raise RuntimeError("Logging manager `{}` already exists".format(self.name))
#         LoggableFuncManager._loggables_by_name[self.name] = self
#         LoggableFuncManager._dangling_loggables.remove(self)
#         if on:
#             if names.should_be_on(self._name) == '+':
#                 self.on()
#             else:
#                 self.off()
#         return self

#     def on(self):
#         """ Turn on logging for this manager

#         Calls already in progress won't be logged
#         """
#         self.wrapper = LogFuncWrapper(self, self.printed_name, self.parent, self.property_name, self.func_name)
#         if isinstance(self.wrapper._func, LogFuncWrapper):
#             self.wrapper = self.wrapper._func
#         if self.name == self.printed_name:
#             main.just_info('logging: + {}'.format(self._name))
#         else:
#             main.just_info('logging: + {}     (as {})'.format(self._name, self.printed_name))

#     def off(self):
#         """ Turn off logging for this manager

#         Calls already in progress will be logged
#         """
#         if self.name == self.printed_name:
#             main.just_info('logging: - {}'.format(self._name))
#         else:
#             main.just_info('logging: - {}     (as {})'.format(self._name, self.printed_name))
#         if self.wrapper is not None:
#             self.wrapper.remove_yourself()
#         self.wrapper = None
