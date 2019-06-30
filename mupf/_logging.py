import logging
import sys
import os

call_id = 0
indent = 0

def logged(f):

    def wrap(*args, **kwargs):
        global call_id, indent
        head = f.__code__.co_filename
        tail = ""
        filename = []
        while tail != 'mupf':
            filename.append(tail)
            head, tail = os.path.split(head)
        filename.reverse()
        filename = "/".join(filename) 
        logger = logging.getLogger('mupf')
        frameid = call_id
        call_id += 1
        indent_sp = "|"*indent
        logger.info("{},-< {}{}:{} ({},{})".format(indent_sp,filename, f.__code__.co_name, frameid, repr(args), repr(kwargs)))
        indent += 1
        result = f(*args, **kwargs)
        indent -= 1
        logger.info("{}'-> {}{}:{} => {}".format(indent_sp,filename,f.__code__.co_name, frameid, repr(result)))
        return result
    
    return wrap