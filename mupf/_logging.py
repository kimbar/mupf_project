import logging
import sys
import os
import threading
import re

lock = threading.Lock()

call_id = 0

indent_by_threadid = {}
number_by_threadid = {}
threads = []

def logged(f):

    def wrap(*args, **kwargs):
        global call_id, indent_by_threadid, lock
        with lock:
            thread = threading.get_ident()
            if thread not in indent_by_threadid:
                indent_by_threadid[thread] = 0
                number_by_threadid[thread] = len(indent_by_threadid)
                threads.append(thread)
            
            indent = indent_by_threadid[thread]
            number = number_by_threadid[thread]

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
            frameid = call_id
            call_id += 1
            if number == 1:
                indent_sp = "│"*indent
                start_knee = "┌─"
                end_knee = "└─"
            elif number == 2:
                indent1 = indent_by_threadid[threads[0]]
                indent_sp = "│"*indent1+" "*(20-indent1)+"║"*indent
                start_knee = "╔═"
                end_knee = "╚═"
            funcname = f.__qualname__.replace('create_command_class_for_client.<locals>.Command','Command')
            logger.info("{}{}< {}{}:{}           ({}, {})".format(
                indent_sp,
                start_knee,
                filename,
                funcname,
                frameid,
                ", ".join([repr(a) for a in args]),
                ", ".join([k+"="+repr(v) for k,v in kwargs.items()]),
            ))
            indent_by_threadid[thread] += 1

        result = f(*args, **kwargs)

        with lock:
            indent_by_threadid[thread] -= 1
            if number == 1:
                indent_sp = "│"*indent
                start_knee = "┌─"
                end_knee = "└─"
            elif number == 2:
                indent1 = indent_by_threadid[threads[0]]
                indent_sp = "│"*indent1+" "*(20-indent1)+"║"*indent
                start_knee = "╔═"
                end_knee = "╚═"
            logger.info("{}{}> {}{}:{}           => {}".format(
                indent_sp,
                end_knee,
                filename,
                funcname,
                frameid,
                repr(result),
            ))
            return result
    
    return wrap