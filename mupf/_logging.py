import logging
import sys
import os
import threading
import re

lock = threading.Lock()

indent_by_threadid = {}
thread_number_by_threadid = {}
threads = []
call_count = {}


def enable_logging(filename):
    logging.basicConfig(level=logging.DEBUG)
    hand = logging.FileHandler(filename=filename, mode='w', encoding='utf-8')
    hand.setFormatter(logging.Formatter(fmt='[%(name)s] %(message)s'))
    logging.getLogger('').addHandler(hand)


def logged(f):

    def wrap(*args, **kwargs):
        global call_id, indent_by_threadid, lock
        with lock:
            thread = threading.get_ident()
            if thread not in indent_by_threadid:
                indent_by_threadid[thread] = 0
                thread_number_by_threadid[thread] = len(indent_by_threadid)
                threads.append(thread)
            
            indent = indent_by_threadid[thread]
            thread_number = thread_number_by_threadid[thread]

            head = f.__code__.co_filename
            tail = ""
            filename = []
            while tail != 'mupf':
                filename.append(tail)
                head, tail = os.path.split(head)
            filename.reverse()
            filename = "/".join(filename) 
            thread = threading.get_ident()
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

            funcname = f.__qualname__.replace('create_command_class_for_client.<locals>.Command','Command')

            call_count[filename+funcname] = call_count.get(filename+funcname,-1)+1
            call_number = call_count[filename+funcname]

            msg = "{4} {0}┌─ {1}{2}-{3}".format(indent_sp, filename, funcname, call_number, thread_abr)
            lmsg = max(((len(msg)-10)//20+2)*20,80)
            msg += " "*(lmsg-len(msg)) + "( {} )".format(", ".join([repr(a) for a in args]+[k+"="+repr(v) for k,v in kwargs.items()]))
            logger.info(msg)
            indent_by_threadid[thread] += 1

        result = f(*args, **kwargs)

        with lock:
            indent_by_threadid[thread] -= 1
            if thread_number == 1:
                indent_sp = "│"*indent
            elif thread_number == 2:
                indent1 = indent_by_threadid[threads[0]]
                indent_sp = "│"*indent1+"·"*(10-indent1)+"│"*indent
            else:
                indent_sp = ""

            msg = "{4} {0}└─ {1}{2}-{3}".format(indent_sp, filename, funcname, call_number, thread_abr)
            lmsg = max(((len(msg)-10)//20+2)*20,80)
            msg += " "*(lmsg-len(msg)) + "  => {}".format(repr(result))
            logger.info(msg)

            return result
    
    return wrap