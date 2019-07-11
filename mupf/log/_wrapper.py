import copy
import logging
import threading
from . import _verbosity as verbosity
from . import _tracks as tracks
from ._main import lock, THREAD_TAB_WIDTH, TAB_WIDTH, MIN_COLUMN_WIDTH, thread_number_by_threadid

class LogFuncWrapper:
    """ Object is a wrapper for a callable that calls the callable but also logs

    The callable is replaced by the object, and the object does logging before
    the call and after the call of the callable. The start and end of a call
    is joined by the graph. Alternativelly, calls of a single callable can be
    joined by a graph until explicitly ended (`joined` version). 
    """

    def __init__(self, manager, printed_name, parent, property_name, func_name):
        if property_name is None:
            self._func = getattr(parent, func_name)
        else:
            self._func = getattr(parent.__getattribute__(parent, property_name), func_name)
        if isinstance(self._func, LogFuncWrapper):
            return
        self._manager = manager
        self._printed_name = printed_name
        self._parent = parent
        self._property_name = property_name
        self._func_name = func_name
        self._verbosity_manager = None
        self._call_number = None
        self._obj_repr = ''
        self.track = "?"
        if self._property_name is None:
            setattr(parent, func_name, self)
        else:
            prop = parent.__getattribute__(parent, self._property_name)
            decor_name = {'fget':'getter', 'fset':'setter', 'fdel': 'deleter'}[func_name]
            setattr(parent, self._property_name, getattr(prop, decor_name)(self))

    def __get__(self, obj, class_):
        method = copy.deepcopy(self)
        method._func = method._func.__get__(obj, class_)
        if obj is not None:
            method._printed_name = method._printed_name.replace('<>', verbosity.enh_repr(obj, short=True), 1)
        return method
    
    def __call__(self, *args, **kwargs):

        # This part simulates `__get__` for a property.
        if self._property_name is not None and not hasattr(self._func, '__self__'):
            method = copy.copy(self)
            # bind the function with object
            method._func = method._func.__get__(args[0], self._parent)
            method._obj_repr = verbosity.enh_repr(args[0], short=True)
            # rerun itself (copy), but w/o first argument (self)
            return method(*args[1:], **kwargs)

        with lock:
            self._verbosity_manager = copy.copy(self._manager.verbosity_manager)
            # if self._verbosity_manager._joined:
            #     self._verbosity_manager.set_joined_part(args[0])
            
            self._call_number = self._manager.call_count
            if (not self._verbosity_manager._joined) or args[0] == 'end':
                self._manager.call_count += 1

            if self._verbosity_manager._is_range or (self._verbosity_manager._joined and args[0] == 'start'):
                thread_number, thread_abr = self._identify_thread()
                self.track = tracks.find_free((thread_number-1)*THREAD_TAB_WIDTH)
                tracks.reserve(self.track)

            if self._verbosity_manager._log_enter or (self._verbosity_manager._joined and args[0] == 'start'):
                if self._verbosity_manager._joined:
                    self._precall_log(*args[1:], **kwargs)
                else:
                    self._precall_log(*args, **kwargs)

        # Actual call of the wrapee
        result = self._func(*args, **kwargs)

        with lock:
            if self._verbosity_manager._log_exit and not self._verbosity_manager._joined:
                self._postcall_log(result)
            if (self._verbosity_manager._joined and args[0] == 'end'):
                self._postcall_log(*args[1:], **kwargs)
            if self._verbosity_manager._joined and args[0] == 'mid':
                self._midcall_log(*args[1:], **kwargs)
            if self._verbosity_manager._is_range or (self._verbosity_manager._joined and args[0] == 'end'):
                tracks.free(self.track)

        return result

    def remove_yourself(self, *args, **kwargs) -> bool:
        """ Detach the object, and put back the original function there
        """
        if self._property_name is None:
            setattr(self._parent, self._func_name, self._func)
        else:
            prop = self._parent.__getattribute__(self._parent, self._property_name)
            num = ['fget', 'fset', 'fdel'].index(self._func_name)
            is_wrapped = list(map(lambda x: isinstance(x,LogFuncWrapper), [prop.fget, prop.fset, prop.fdel]))
            if is_wrapped[num]:
                decor_name = ['getter', 'setter', 'deleter'][num]
                setattr(self._parent, self._property_name, getattr(prop, decor_name)(self._func))

    def _identify_thread(self):
        global thread_number_by_threadid
        threadid = threading.get_ident()
        if threadid not in thread_number_by_threadid:
            thread_number_by_threadid[threadid] = len(thread_number_by_threadid)+1
        thread_number = thread_number_by_threadid[threadid]
        if thread_number == 1:
            thread_abr = 'main'
        elif thread_number == 2:
            thread_abr = 'serv'
        else:
            thread_abr = 'th-?'
        return thread_number, thread_abr

    @staticmethod
    def _make_line(thread_abr, tracks, branch_end, name, ruler):
        msg = "{0} {1}─{2} {3}".format(thread_abr, tracks, branch_end, name)
        lmsg = max(((len(msg)-MIN_COLUMN_WIDTH+(TAB_WIDTH//2))//TAB_WIDTH+1)*TAB_WIDTH, 0) + MIN_COLUMN_WIDTH
        msg += " "*(lmsg-len(msg)) + ruler
        return msg

    def _make_name(self):
        return "{}/{}".format(self._printed_name.replace('<>', self._obj_repr), self._call_number)

    def _precall_log(self, *args, **kwargs):
        """ Log what's before the call
        """
        thread_number, thread_abr = self._identify_thread()
        if self._verbosity_manager._log_exit or self._verbosity_manager._joined:
            line_tracks = tracks.write('start', self.track)
        else:
            line_tracks = tracks.write().ljust((thread_number-1)*THREAD_TAB_WIDTH) + ' '
        msg = self._make_line(thread_abr, line_tracks, '<', self._make_name(), "<┤  ")         
        if (len(args) or len(kwargs)):
            if self._verbosity_manager._log_args:
                msg += ", ".join([verbosity.enh_repr(a) for a in args]+[k+"="+verbosity.enh_repr(v) for k,v in kwargs.items()])
            else:
                msg += "..."
        logging.getLogger('mupf').info(msg)

    def _postcall_log(self, *args, **kwargs):
        """ Log what's after the call
        """
        thread_number, thread_abr = self._identify_thread()
        if self._verbosity_manager._log_enter or self._verbosity_manager._joined:
            line_tracks = tracks.write('end', self.track)
        else:
            line_tracks = tracks.write().ljust((thread_number-1)*THREAD_TAB_WIDTH) + ' '
        msg = self._make_line(thread_abr, line_tracks, '>', self._make_name(), " ├> ")
        if (len(args) or len(kwargs)) and (len(kwargs) or len(args)!=1 or args[0] is not None):
            if self._verbosity_manager._log_results:
                msg += ", ".join([verbosity.enh_repr(a) for a in args]+[k+"="+verbosity.enh_repr(v) for k,v in kwargs.items()])
            else:
                msg += "..."
        logging.getLogger('mupf').info(msg)

    def _midcall_log(self, *args, **kwargs):
        """ Log in the middle of the graph when `joined` version is on
        """
        thread_number, thread_abr = self._identify_thread()
        line_tracks = tracks.write('mid', self.track)
        msg = self._make_line(thread_abr, line_tracks, '╴', self._make_name(), " ├╴ ")
        if (len(args) or len(kwargs)):
            msg += ", ".join([verbosity.enh_repr(a) for a in args]+[k+"="+verbosity.enh_repr(v) for k,v in kwargs.items()])
        logging.getLogger('mupf').info(msg)
