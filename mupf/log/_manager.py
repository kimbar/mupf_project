from . import _main as main
from . import _wrapper
from ._wrapper import LogFuncWrapper
from . import _names as names

class LoggableFuncManager:
    """ Object represents a POSIBILITY of logging of a function/method/property

    The logging is turned on by `LoggableFuncManager.on()`
    """
    _loggables_by_name = {}
    _dangling_loggables = []

    def __init__(self, name, parent, func_name, verbosity_manager):
        if name in LoggableFuncManager._loggables_by_name:
            raise ValueError('Loggable name `{}` already exists'.format(name))
        self.parent = parent              # the object (class or module) that holds the method/function/property
        self.func_name = func_name        # the name of the function that is wrapped
        self.verbosity_manager = verbosity_manager
        self._name = None                 # the name of manager (accesed by property)
        self.printed_name = None          # the name of manager actually printed in the log
        self.wrapper = None               # the wrapper for function doing the actual logging
        self.call_count = 0               # how many counts of this manager's function has been done
        self.property_name = None         # property name if the function is actually an accesor of property
        # self.log_path = log_path          # should the "path" part of the name be logged in the output
        # self.log_args = log_args          # should the args of a call be logged
        # self.log_results = log_results    # should the results of a call be logged
        # self.log_enter = log_enter        # should the call begining be logged
        # self.log_exit = log_exit          # should the call ending be logged
        # self.joined = joined              # is it a `joined` version of logging graph

        # tidy up the `name` and `printed_name` things
        self.name = name
        # The manager is dangling until added to the registry
        LoggableFuncManager._dangling_loggables.append(self)

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        if self.verbosity_manager._log_path:
            self.printed_name = value
        else:
            self.printed_name = names.build_path([names.parse_path(value)[-1]])

    def add(self, on=False):
        """ Add the manager to the registry
        """
        if self.name in LoggableFuncManager._loggables_by_name:
            raise RuntimeError("Logging manager `{}` already exists".format(self.name))
        LoggableFuncManager._loggables_by_name[self.name] = self
        LoggableFuncManager._dangling_loggables.remove(self)
        if on:
            if names.should_be_on(self._name) == '+':
                self.on()
            else:
                self.off()
        return self

    def on(self):
        """ Turn on logging for this manager

        Calls already in progress won't be logged
        """
        self.wrapper = LogFuncWrapper(self, self.printed_name, self.parent, self.property_name, self.func_name)
        if isinstance(self.wrapper._func, LogFuncWrapper):
            self.wrapper = self.wrapper._func
        if self.name == self.printed_name:
            main.just_info('logging: + {}'.format(self._name))
        else:
            main.just_info('logging: + {}     (as {})'.format(self._name, self.printed_name))

    def off(self):
        """ Turn off logging for this manager

        Calls already in progress will be logged
        """
        if self.name == self.printed_name:
            main.just_info('logging: - {}'.format(self._name))
        else:
            main.just_info('logging: - {}     (as {})'.format(self._name, self.printed_name))
        if self.wrapper is not None:
            self.wrapper.remove_yourself()
        self.wrapper = None

def refresh():
    for l in LoggableFuncManager._loggables_by_name.values():
        if names.should_be_on(l.name) == '+':
            l.on()
        else:
            l.off()