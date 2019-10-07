from . import _address as address
from . import _main as main
from . import _writer as writer
from . import settings
from ._event import LogEvent
from ._sentinel import LogFunctionSentinel, LogPropertySentinel


class LogManager:

    _managers_by_addr = {}
    
    def __init__(self, addr, log_path=True, hidden=False):
        self.log_path = log_path
        self._addr = None
        self.printed_addr_tree = None
        self.addr = addr
        self._state = None
        self._writer_count = 0               # how many counts of this manager's function has been done
        self._writers = {}
        self._hidden = hidden
        self._current_event = None
        self._employed_managers = []

    @property
    def addr(self):
        return self._addr

    @addr.setter
    def addr(self, value):
        self._addr = value
        if self.log_path:
            self.printed_addr_tree = address.parse_path(value)
        else:
            self.printed_addr_tree = [address.parse_path(value)[-1]]

    def log_state_change(self, state):
        printed_addr = address.build_path(self.printed_addr_tree)
        with main.log_mutex:
            if self._addr == printed_addr:
                writer.just_info('state: {} {}'.format(state, self._addr))
            else:
                writer.just_info('state: {} {}      as {}'.format(state, self._addr, printed_addr))

    def on(self):
        """ Turn on logging for this manager

        Calls already in progress won't be logged
        """
        if self._hidden:
            self.off()
            return
        if self._state != True:
            self.log_state_change('+')
        self._state = True

    def off(self):
        """ Turn off logging for this manager

        Calls already in progress will be logged
        """
        if self._state or (settings.log_state_of_switched_off_managers and self._state is None):
            if self._hidden:
                self.log_state_change('H')
            else:
                self.log_state_change('-')
        self._state = False

    def add(self, auto_on=False):
        """ Add the manager to the registry
        """
        if self._addr in LogManager._managers_by_addr:
            writer.just_info('ERROR: Adding `{}` manager failed - address already exists'.format(self._addr))
            return False
        LogManager._managers_by_addr[self._addr] = self
        if auto_on:
            if address.should_be_on(self._addr) == '+':
                self.on()
            else:
                self.off()
        refresh(only_aunts=True)
        return True

    def on_event(self, event):
        raise NotImplementedError('`LogManager.on_event()` not in `{}`'.format(self))

    def new_writer(self, * , printed_addr=None, style=None, group=None):
        if printed_addr is None:
            printed_addr = self._addr
        if style is None:
            style = writer.LogWriterStyle.inner + writer.LogWriterStyle.multi_line
        if group is None:
            group = main.group_selector(self._current_event)
        with main.log_mutex:
            id_ = self._writer_count
            self._writer_count += 1
        wr = writer.LogWriter(id_, printed_addr, style, group)
        self._writers[id_] = wr   # TODO: more sophisticated
        return wr

    def find_writer(self, id_):
        return self._writers[id_]
    
    def delete_writer(self, id_):
        del self._writers[id_]

    def employ_sentinels(self, empl_addr, nickname=None):
        re = address.make_regexp_from_filter(empl_addr)
        count = 0
        for addr, manager in self._managers_by_addr.items():
            if isinstance(manager, LogSimpleManager) and re.match(addr):
                manager.employ(self, nickname)
                count += 1
                if manager not in self._employed_managers:
                    self._employed_managers.append(manager)
        return count
        
    def dismiss_all_sentinels(self):
        for manager in self._employed_managers:
            manager.dismiss()
        del self._employed_managers[:]

    @property
    def state(self):
        return self._state

    @staticmethod
    def group_selector(event):
        return main.group_selector(event)

    @staticmethod
    def format_args(fargs=None, fkwargs=None):
        if isinstance(fargs, LogEvent):
            return ", ".join([writer.enh_repr(a) for a in fargs.args]+[k+"="+writer.enh_repr(v) for k,v in fargs.kwargs.items()])
        if fargs is None:
            fargs = []
        if fkwargs is None:
            fkwargs = {}
        return ", ".join([writer.enh_repr(a) for a in fargs]+[k+"="+writer.enh_repr(v) for k,v in fkwargs.items()])


class LogSimpleManager(LogManager):

    _dangling_simple_managers = []

    def __init__(self, addr, log_path, func_parent, func_name, verbosity_settings, hidden):
        self.func_parent = func_parent              # the object (class or module) that holds the method/function/property
        self.func_name = func_name        # the name of the function that is wrapped
        
        self.sentinel = None               # the wrapper for function doing the actual logging
        self.property_name = None         # property name if the function is actually an accesor of property
        self.aunt_nicknames = {}
        self._employed = False
        self._silent_events_count = 0

        self._log_args = verbosity_settings['log_args']
        self._log_results = verbosity_settings['log_results']
        self._log_enter = verbosity_settings['log_enter']
        self._log_exit = verbosity_settings['log_exit']
        self._log_path = verbosity_settings['log_path']

        super().__init__(addr, log_path, hidden)
        LogSimpleManager._dangling_simple_managers.append(self)
    
    def add(self, auto_on=False):
        if not super().add(auto_on):
            return False
        LogSimpleManager._dangling_simple_managers.remove(self)
        return True

    def set_as_property_manager(self, property_name, func_name):
        self.property_name = property_name
        self.func_name = func_name

    def _soft_on(self):
        """ Only activate sentinel, do not turn on logging
        """
        if self.sentinel is not None:
            return
        if self.property_name is None:
            self.sentinel = LogFunctionSentinel(self, self.func_parent, self.func_name)
        else:
            self.sentinel = LogPropertySentinel(self, self.func_parent, self.property_name, self.func_name)
        # If wrapped a sentinel, then unwrap the monad
        # this loop makes `on()` method idempotent
        while not self.sentinel.is_first_level:
            self.sentinel = self.sentinel._func

    def on(self):
        self._soft_on()
        super().on()

    def _soft_off(self):
        """ Only deactivate sentinel
        """
        if self._employed:
            return
        if self.sentinel is not None:
            self.sentinel.remove_yourself()
        self.sentinel = None
    
    def off(self):
        self._soft_off()
        super().off()

    def employ(self, aunt, nickname=None):
        self.aunt_nicknames[aunt] = nickname
        self._employed = True
        if self.sentinel is None:
            self._soft_on()

    def dismiss(self, aunt):
        del self.aunt_nicknames[aunt]
        if len(self.aunt_nicknames) == 0:
            self._employed = False
        if self._state == False:
            self._soft_off()

    def on_event(self, event):
        self._current_event = event
        if self._state:
            wr = None
            if event.entering():
                wr = self.new_writer(
                    printed_addr = event.sentinel._printed_addr,
                    style = writer.LogWriterStyle.inner+(writer.LogWriterStyle.multi_line if (self._log_enter and self._log_exit) else writer.LogWriterStyle.single_line),
                )
                event._call_id = wr.id_
                if self._log_enter:
                    if self._log_args:
                        wr.write(self.format_args(event))
                    else:
                        wr.write()
            elif self._log_exit:
                wr = self.find_writer(id_=event.call_id)
                if self._log_results:
                    wr.write(writer.enh_repr(event.result), finish=True)
                else:
                    wr.write(finish=True)
            if wr is not None and wr.finished:
                self.delete_writer(wr.id_)
        elif event.entering():
            # There is no writer, because the sentinel is only employed
            # but the event still needs a `call_id_`. A negative number is given
            with main.log_mutex:
                event._call_id = -1 - self._silent_events_count
                self._silent_events_count += 1
        self._current_event = None
            
        for aunt, nickname in self.aunt_nicknames.items():
            event._sentinel_nickname = nickname
            aunt._current_event = event
            aunt.on_event(event)
            aunt._current_event = None


def refresh(only_aunts=False):
    if not main._logging_enabled:
        return
    aunts = []
    with main.log_mutex:
        for manager in LogManager._managers_by_addr.values():
            if isinstance(manager, LogSimpleManager):
                if not only_aunts:
                    _refresh_manager(manager)
            else:
                aunts.append(manager)
        for manager in aunts:
            _refresh_manager(manager)

def _refresh_manager(manager):
    if address.should_be_on(manager.addr) == '+':
        manager.on()
    else:
        manager.off()
