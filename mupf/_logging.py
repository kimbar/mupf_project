import logging
import sys
import os
import threading
import re
import types
import inspect
import copy

lock = threading.Lock()
thread_number_by_threadid = {}
call_count = {}    # FIXME: this will leak -- destroyed objects still keep track of their call count
_tracks = []


def _is_track_occupied(n):
    global _tracks
    if n >= len(_tracks):
        return False
    else:
        return _tracks[n]

def _reserve_track(n):
    global _tracks
    if n >= len(_tracks):
        _tracks += [False]*(n-len(_tracks)+1)
    _tracks[n] = True

def _free_track(n):
    global _tracks
    _tracks[n] = False
    while not _tracks[-1]:
        _tracks.pop()
        if len(_tracks) == 0:
            break

def _find_free_track(min_=0):
    while _is_track_occupied(min_):
        min_ += 1
    return min_

def _repr_tracks(branch=None, branch_track=None):
    global _tracks
    result = ""
    for n, track in enumerate(_tracks):
        if track:
            if branch:
                if n < branch_track:
                    result += "│"
                elif n == branch_track:
                    if branch == 'start':
                        result += "┌"
                    elif branch == 'end':
                        result += "└"
                    else:
                        result += "├"
                elif n > branch_track:
                    result += "┼"
            else:
                result += "│"
        else:
            if branch:
                if n < branch_track:
                    result += " "
                elif n == branch_track:
                    result += "?"
                elif n > branch_track:
                    result += "─"
            else:
                result += " "
    return result


class LoggableFunc:

    _loggables_by_name = {}
    _dangling_loggables = []

    def __init__(self, name, parent, target, func_name):
        if name in LoggableFunc._loggables_by_name:
            raise ValueError('Loggable name `{}` already exists'.format(name))
        self.parent = parent
        self.target = target
        self.name = name
        self.func_name = func_name
        self.log_args = True
        self.log_results = True
        self.log_enter = True
        self.log_exit = True
        self.wrapper = None
        self.call_count = 0
        LoggableFunc._dangling_loggables.append(self)

    def add(self):
        LoggableFunc._loggables_by_name[self.name] = self
        LoggableFunc._dangling_loggables.remove(self)
        return self

    @classmethod
    def remove(cls, name):
        pass

    def on(self):
        self.wrapper = LogFuncWrapper(self.name, self.parent, self.func_name, self.log_args, self.log_results, self.log_enter, self.log_exit)

    def off(self):
        setattr(self.parent, self.func_name, self.wrapper._func)
        self.wrapper = None


class LogFuncWrapper:

    def __init__(self, log_name, parent, func_name, log_args, log_results, log_enter, log_exit):
        self._func = getattr(parent, func_name)
        if isinstance(self._func, LogFuncWrapper):
            return
        self._log_name = log_name
        self._func_name = func_name
        self._log_args = log_args
        self._log_result = log_results
        self._log_enter = log_enter
        self._log_exit = log_exit
        self._parent = parent
        self._is_range = log_enter and log_exit
        setattr(parent, func_name, self)

    def __get__(self, obj, class_):
        method = copy.copy(self)
        method._func = method._func.__get__(obj, class_)
        if obj is not None:
            method._log_name = method._log_name.replace('@', repr(obj), 1)
        return method
    
    def __call__(self, *args, **kwargs):
        global lock
        with lock:
            call_count[self._log_name] = call_count.get(self._log_name,-1)+1
            if self._is_range:
                thread_number, thread_abr = self._identify_thread()
                self.track = _find_free_track((thread_number-1)*10)
                _reserve_track(self.track)
            if self._log_enter:
                self._precall_log(*args, **kwargs)

        result = self._func(*args, **kwargs)

        with lock:
            if self._log_exit:
                self._postcall_log(result)
            if self._is_range:
                _free_track(self.track)
        return result

    def remove_logger(self, *args, **kwargs):
        setattr(self._parent, self._func_name, self._func)

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

    def _precall_log(self, *args, **kwargs):
        thread_number, thread_abr = self._identify_thread()
        call_number = call_count[self._log_name]
        if self._log_exit:
            tracks = _repr_tracks('start', self.track)
        else:
            tracks = _repr_tracks().ljust((thread_number-1)*10) + ' '
        msg = "{3} {0}─< {1}/{2}".format(tracks, self._log_name.replace('@',''), call_number, thread_abr)
        lmsg = max(((len(msg)-10)//20+2)*20,80)
        if self._log_args and (len(args) or len(kwargs)):
            msg += " "*(lmsg-len(msg)) + "<- {}".format(", ".join([repr(a) for a in args]+[k+"="+repr(v) for k,v in kwargs.items()]))
        
        logging.getLogger('mupf').info(msg)

    def _postcall_log(self, result):
        thread_number, thread_abr = self._identify_thread()
        call_number = call_count[self._log_name]
        if self._log_enter:
            tracks = _repr_tracks('end', self.track)
        else:
            tracks = _repr_tracks().ljust((thread_number-1)*10) + ' '
        msg = "{3} {0}─> {1}/{2}".format(tracks, self._log_name.replace('@',''), call_number, thread_abr)
        lmsg = max(((len(msg)-10)//20+2)*20,80)
        if self._log_result and result is not None:
            msg += " "*(lmsg-len(msg)) + "-> {}".format(repr(result))
        
        logging.getLogger('mupf').info(msg)


def loggable(log_name='*', log_args=True, log_results=True, log_enter=True, log_exit=True):
    def loggable_decorator(x):
        nonlocal log_name, log_args, log_results, log_enter, log_exit
        if isinstance(x, types.FunctionType):
            log_name = log_name.replace('*',  x.__name__, 1)
            if x.__qualname__ != x.__name__:
                x._methodtolog = LoggableFunc(log_name, None, x, x.__name__)
                x._methodtolog.log_args = log_args
                x._methodtolog.log_results = log_results
                x._methodtolog.log_enter = log_enter
                x._methodtolog.log_exit = log_exit
            else:
                lf = LoggableFunc(log_name, inspect.getmodule(x), x, x.__name__).add()
                lf.log_args = log_args
                lf.log_results = log_results
                lf.log_enter = log_enter
                lf.log_exit = log_exit
        elif isinstance(x, classmethod):
            log_name = log_name.replace('*',  x.__func__.__name__, 1)
            x.__func__._methodtolog = LoggableFunc(log_name, None, x, x.__func__.__name__)
            x.__func__._methodtolog.log_args = log_args
            x.__func__._methodtolog.log_results = log_results
            x.__func__._methodtolog.log_enter = log_enter
            x.__func__._methodtolog.log_exit = log_exit
        elif isinstance(x, type):
            log_name = log_name.replace('*',  x.__name__, 1)
            for prop_name in dir(x):
                property_ = getattr(x, prop_name)
                try:
                    property_._methodtolog.name = log_name + '.' + property_._methodtolog.name
                    property_._methodtolog.parent = x
                    property_._methodtolog.add()
                    del property_._methodtolog
                except Exception as e:
                    pass
        return x
    return loggable_decorator

class Loggable:

    def __init__(cls, name, bases, dict_):    # pylint: disable=no-self-argument
        lgd = loggable(log_name=name)
        lgd(cls)
        for l in LoggableFunc._loggables_by_name.values():
            l.on()


def enable_logging(filename):
    logging.basicConfig(level=logging.INFO)
    hand = logging.FileHandler(filename=filename, mode='w', encoding='utf-8')
    hand.setFormatter(logging.Formatter(fmt='[%(name)s] %(message)s'))
    logging.getLogger('').addHandler(hand)
    for l in LoggableFunc._loggables_by_name.values():
        l.on()
