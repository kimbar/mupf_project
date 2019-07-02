import logging
import sys
import os
import threading
import re
import types
import inspect
import copy

lock = threading.Lock()
indent_by_threadid = {}
thread_number_by_threadid = {}
threads = []
call_count = {}
_loggables = {}


class LogFuncWrapper:

    def __init__(self, log_name, parent, func_name):
        self._func = getattr(parent, func_name)
        if isinstance(self._func, LogFuncWrapper):
            return
        self._log_name = log_name
        self._func_name = func_name
        self._parent = parent
        self._self = ()
        setattr(parent, func_name, self)

    def __get__(self, obj, objtype=None):
        method = copy.copy(self)
        method._self = (obj,)
        return method

    # def __del__(self):
    #     print('LogFuncWrapper dropped', self._self, self._parent, self._log_name)
    
    def __call__(self, *args, **kwargs):
        global lock
        args = self._self + args
        with lock:
            self._precall_log(*args, **kwargs)

        result = self._func(*args, **kwargs)

        with lock:
            self._postcall_log(result)
        return result

    def remove_logger(self, *args, **kwargs):
        setattr(self._parent, self._func_name, self._func)

    def _precall_log(self, *args, **kwargs):
        global indent_by_threadid, thread_number_by_threadid, threads
        thread = threading.get_ident()
        if thread not in indent_by_threadid:
            indent_by_threadid[thread] = 0
            thread_number_by_threadid[thread] = len(indent_by_threadid)
            threads.append(thread)
        
        indent = indent_by_threadid[thread]
        thread_number = thread_number_by_threadid[thread]

        logger = logging.getLogger('mupf')

        if thread_number == 1:
            indent_sp = "│"*indent
            thread_abr = 'th-M'
        elif thread_number == 2:
            thread_abr = 'th-S'
            indent1 = indent_by_threadid[threads[0]]
            indent_sp = "│"*indent1+"·"*(10-indent1)+"│"*indent
        else:
            indent_sp = ""
            thread_abr = 'th-?'

        call_count[self._log_name] = call_count.get(self._log_name,-1)+1
        call_number = call_count[self._log_name]

        msg = "{3} {0}┌─ {1}-{2}".format(indent_sp, self._log_name, call_number, thread_abr)
        lmsg = max(((len(msg)-10)//20+2)*20,80)
        msg += " "*(lmsg-len(msg)) + "( {} )".format(", ".join([repr(a) for a in args]+[k+"="+repr(v) for k,v in kwargs.items()]))
        logger.info(msg)
        indent_by_threadid[thread] += 1

    def _postcall_log(self, result):
        global indent_by_threadid, thread_number_by_threadid, threads
        thread = threading.get_ident()
        indent_by_threadid[thread] -= 1
        thread_number = thread_number_by_threadid[thread]
        indent = indent_by_threadid[thread]
        if thread_number == 1:
            indent_sp = "│"*indent
            thread_abr = 'th-M'
        elif thread_number == 2:
            thread_abr = 'th-S'
            indent1 = indent_by_threadid[threads[0]]
            indent_sp = "│"*indent1+"·"*(10-indent1)+"│"*indent
        else:
            indent_sp = ""
            thread_abr = 'th-?'

        call_number = call_count[self._log_name]

        msg = "{3} {0}└─ {1}-{2}".format(indent_sp, self._log_name, call_number, thread_abr)
        lmsg = max(((len(msg)-10)//20+2)*20,80)
        msg += " "*(lmsg-len(msg)) + "  => {}".format(repr(result))
        logger = logging.getLogger('mupf')
        logger.info(msg)


def loggable(log_name='*'):
    def loggable_decorator(x):
        global _loggables
        nonlocal log_name
        log_name = log_name.replace('*',  x.__name__, 1)
        if type(x) == types.FunctionType:
            if x.__qualname__ != x.__name__:
                x._methodtolog = log_name
            else:
                _loggables[log_name] = (inspect.getmodule(x), x, x.__name__)
        elif type(x) == type:
            for key in dir(x):
                p = getattr(x, key)
                if hasattr(p, '_methodtolog'):
                    _loggables[log_name+'.'+p._methodtolog] = (x, p, p.__name__)
                    del p._methodtolog
        return x
    return loggable_decorator

def log_on(*names):
    global _loggables
    if len(names) == 0:
        names = _loggables.keys()
    for name in names:
        parent, target, func_name = _loggables[name]
        LogFuncWrapper(name, parent, func_name)

def log_off(*names):
    global _loggables
    if len(names) == 0:
        names = _loggables.keys()
    for name in names:
        parent, target, func_name = _loggables[name]
        func = getattr(parent, func_name)
        if func != target:
            func.remove_logger()

def enable_logging(filename):
    logging.basicConfig(level=logging.DEBUG)
    hand = logging.FileHandler(filename=filename, mode='w', encoding='utf-8')
    hand.setFormatter(logging.Formatter(fmt='[%(name)s] %(message)s'))
    logging.getLogger('').addHandler(hand)
    log_on()
