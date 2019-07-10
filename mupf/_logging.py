# import logging
# import sys
# import os
# import threading
# import re
# import types
# import inspect
# import copy
# import websockets
# import asyncio


# lock = threading.Lock()
# thread_number_by_threadid = {}    # FIXME: this is the old way of things -- to rethink
# _tracks = []
# _logging_enabled = False
# _short_class_repr = {}
# _long_class_repr = {}
# _filters = []

# MIN_COLUMN_WIDTH = 90    # minimum width of the column with names of functions
# TAB_WIDTH = 20           # if the width is not enough, this much is added in one go
# THREAD_TAB_WIDTH = 10    # the spacing for another thread graph column
# rounded_graph_corners = True   # format of the graph ┌─ or ╭─

# def _is_track_occupied(n):
#     """ Check if track is already taken """
#     global _tracks
#     if n >= len(_tracks):
#         return False
#     else:
#         return _tracks[n]

# def _reserve_track(n):
#     """ Reserve a track w/o checking """
#     global _tracks
#     if n >= len(_tracks):
#         _tracks += [False]*(n-len(_tracks)+1)
#     _tracks[n] = True

# def _free_track(n):
#     """ Free a track w/o checking """
#     global _tracks
#     _tracks[n] = False
#     while not _tracks[-1]:
#         _tracks.pop()
#         if len(_tracks) == 0:
#             break

# def _find_free_track(min_=0):
#     """ Find a free track, but at least `min_` one """
#     while _is_track_occupied(min_):
#         min_ += 1
#     return min_

# def _repr_tracks(branch=None, branch_track=None):
#     """ Print tracks for a single line

#     The line is connected to the line (branched) if `branch` number is given. The track number
#     `branch` should be occupied. `branch_track` can have three values: `"start"` or `"end"` if the
#     branch should strart or end the track, and any other value (preffered `"mid"`) if the branch
#     should only attach to a track.
#     """
#     global _tracks, rounded_graph_corners
#     result = ""
#     for n, track in enumerate(_tracks):
#         if track:
#             if branch:
#                 if n < branch_track:
#                     result += "│"
#                 elif n == branch_track:
#                     if branch == 'start':
#                         result += "╭" if rounded_graph_corners else "┌"
#                     elif branch == 'end':
#                         result += "╰" if rounded_graph_corners else "└"
#                     else:
#                         result += "├"
#                 elif n > branch_track:
#                     result += "┼"
#             else:
#                 result += "│"
#         else:
#             if branch:
#                 if n < branch_track:
#                     result += " "
#                 elif n == branch_track:
#                     result += "?"
#                 elif n > branch_track:
#                     result += "─"
#             else:
#                 result += " "
#     return result


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
#         if self.verbosity_manager.log_path:
#             self.printed_name = value
#         else:
#             self.printed_name = build_path([parse_path(value)[-1]])

#     def add(self, on=False):
#         """ Add the manager to the registry
#         """
#         if self.name in LoggableFuncManager._loggables_by_name:
#             raise RuntimeError("Logging manager `{}` already exists".format(self.name))
#         LoggableFuncManager._loggables_by_name[self.name] = self
#         LoggableFuncManager._dangling_loggables.remove(self)
#         if on:
#             if _should_be_on(self._name) == '+':
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
#             just_info('logging: + {}'.format(self._name))
#         else:
#             just_info('logging: + {}     (as {})'.format(self._name, self.printed_name))

#     def off(self):
#         """ Turn off logging for this manager

#         Calls already in progress will be logged
#         """
#         if self.name == self.printed_name:
#             just_info('logging: - {}'.format(self._name))
#         else:
#             just_info('logging: - {}     (as {})'.format(self._name, self.printed_name))
#         if self.wrapper is not None:
#             self.wrapper.remove_yourself()
#         self.wrapper = None


# class LogFuncWrapper:
#     """ Object is a wrapper for a callable that calls the callable but also logs

#     The callable is replaced by the object, and the object does logging before
#     the call and after the call of the callable. The start and end of a call
#     is joined by the graph. Alternativelly, calls of a single callable can be
#     joined by a graph until explicitly ended (`joined` version). 
#     """

#     def __init__(self, manager, printed_name, parent, property_name, func_name):
#         if property_name is None:
#             self._func = getattr(parent, func_name)
#         else:
#             self._func = getattr(parent.__getattribute__(parent, property_name), func_name)
#         if isinstance(self._func, LogFuncWrapper):
#             return
#         self._manager = manager
#         self._printed_name = printed_name
#         self._parent = parent
#         self._property_name = property_name
#         self._func_name = func_name
#         self._verbosity_manager = None
#         self._call_number = None
#         self._obj_repr = ''
#         self.track = "?"
#         if self._property_name is None:
#             setattr(parent, func_name, self)
#         else:
#             prop = parent.__getattribute__(parent, self._property_name)
#             decor_name = {'fget':'getter', 'fset':'setter', 'fdel': 'deleter'}[func_name]
#             setattr(parent, self._property_name, getattr(prop, decor_name)(self))

#     def __get__(self, obj, class_):
#         method = copy.copy(self)
#         method._func = method._func.__get__(obj, class_)
#         if obj is not None:
#             method._log_name = method._log_name.replace('<>', enh_repr(obj, short=True), 1)
#         return method
    
#     def __call__(self, *args, **kwargs):
#         global lock, THREAD_TAB_WIDTH

#         # This part simulates `__get__` for a property.
#         if self._property_name is not None and not hasattr(self._func, '__self__'):
#             method = copy.copy(self)
#             # bind the function with object
#             method._func = method._func.__get__(args[0], self._parent)
#             method._obj_repr = enh_repr(args[0], short=True)
#             # rerun itself (copy), but w/o first argument (self)
#             return method(*args[1:], **kwargs)

#         with lock:
#             self._verbosity_manager = copy.copy(self._manager.verbosity_manager)
#             if self._verbosity_manager._joined:
#                 self._verbosity_manager.set_joined_part(args[0])
            
#             self._call_number = self._manager.call_count
#             # if (not self._joined) or args[0] == 'end':
#             if self._verbosity_manager.do_inc_call_count():
#                 self._manager.call_count += 1

#             self.track = self._verbosity_manager.get_track()
#             # if self._is_range or (self._joined and args[0] == 'start'):
#             if self._verbosity_manager.do_need_new_track():
#                 thread_number, thread_abr = self._identify_thread()
#                 self.track = _find_free_track((thread_number-1)*THREAD_TAB_WIDTH)
#                 _reserve_track(self.track)

#             if self._log_enter or (self._joined and args[0] == 'start'):
#                 if self._joined:
#                     self._precall_log(*args[1:], **kwargs)
#                 else:
#                     self._precall_log(*args, **kwargs)

#         # Actual call of the wrapee
#         result = self._func(*args, **kwargs)

#         with lock:
#             if self._log_exit and not self._joined:
#                 self._postcall_log(result)
#             if (self._joined and args[0] == 'end'):
#                 self._postcall_log(*args[1:], **kwargs)
#             if self._joined and args[0] == 'mid':
#                 self._midcall_log(*args[1:], **kwargs)
#             if self._is_range or (self._joined and args[0] == 'end'):
#                 _free_track(self.track)

#         return result

#     def remove_yourself(self, *args, **kwargs) -> bool:
#         """ Detach the object, and put back the original function there
#         """
#         if self._property_name is None:
#             setattr(self._parent, self._func_name, self._func)
#         else:
#             prop = self._parent.__getattribute__(self._parent, self._property_name)
#             num = ['fget', 'fset', 'fdel'].index(self._func_name)
#             is_wrapped = list(map(lambda x: isinstance(x,LogFuncWrapper), [prop.fget, prop.fset, prop.fdel]))
#             if is_wrapped[num]:
#                 decor_name = ['getter', 'setter', 'deleter'][num]
#                 setattr(self._parent, self._property_name, getattr(prop, decor_name)(self._func))

#     def _identify_thread(self):
#         global thread_number_by_threadid
#         threadid = threading.get_ident()
#         if threadid not in thread_number_by_threadid:
#             thread_number_by_threadid[threadid] = len(thread_number_by_threadid)+1
#         thread_number = thread_number_by_threadid[threadid]
#         if thread_number == 1:
#             thread_abr = 'main'
#         elif thread_number == 2:
#             thread_abr = 'serv'
#         else:
#             thread_abr = 'th-?'
#         return thread_number, thread_abr

#     @staticmethod
#     def _make_line(thread_abr, tracks, branch_end, name, ruler):
#         global MIN_COLUMN_WIDTH, TAB_WIDTH
#         msg = "{0} {1}─{2} {3}".format(thread_abr, tracks, branch_end, name)
#         lmsg = max(((len(msg)-MIN_COLUMN_WIDTH+(TAB_WIDTH//2))//TAB_WIDTH+1)*TAB_WIDTH, 0) + MIN_COLUMN_WIDTH
#         msg += " "*(lmsg-len(msg)) + ruler
#         return msg

#     def _make_name(self):
#         return "{}/{}".format(self._log_name.replace('<>', self._obj_repr), self._call_number)

#     def _precall_log(self, *args, **kwargs):
#         """ Log what's before the call
#         """
#         thread_number, thread_abr = self._identify_thread()
#         if self._log_exit or self._joined:
#             tracks = _repr_tracks('start', self.track)
#         else:
#             tracks = _repr_tracks().ljust((thread_number-1)*THREAD_TAB_WIDTH) + ' '
#         msg = self._make_line(thread_abr, tracks, '<', self._make_name(), "<┤  ")         
#         if (len(args) or len(kwargs)):
#             if self._log_args:
#                 msg += ", ".join([enh_repr(a) for a in args]+[k+"="+enh_repr(v) for k,v in kwargs.items()])
#             else:
#                 msg += "..."
#         logging.getLogger('mupf').info(msg)

#     def _postcall_log(self, *args, **kwargs):
#         """ Log what's after the call
#         """
#         thread_number, thread_abr = self._identify_thread()
#         if self._log_enter or self._joined:
#             tracks = _repr_tracks('end', self.track)
#         else:
#             tracks = _repr_tracks().ljust((thread_number-1)*THREAD_TAB_WIDTH) + ' '
#         msg = self._make_line(thread_abr, tracks, '>', self._make_name(), " ├> ")
#         if (len(args) or len(kwargs)) and (len(kwargs) or len(args)!=1 or args[0] is not None):
#             if self._log_result:
#                 msg += ", ".join([enh_repr(a) for a in args]+[k+"="+enh_repr(v) for k,v in kwargs.items()])
#             else:
#                 msg += "..."
#         logging.getLogger('mupf').info(msg)

#     def _midcall_log(self, *args, **kwargs):
#         """ Log in the middle of the graph when `joined` version is on
#         """
#         thread_number, thread_abr = self._identify_thread()
#         tracks = _repr_tracks('mid', self.track)
#         msg = self._make_line(thread_abr, tracks, '╴', self._make_name(), " ├╴ ")
#         if (len(args) or len(kwargs)):
#             msg += ", ".join([enh_repr(a) for a in args]+[k+"="+enh_repr(v) for k,v in kwargs.items()])
#         logging.getLogger('mupf').info(msg)


# class VerbosityManager:
#     def __init__(self, log_args, log_results, log_enter, log_exit, log_path, joined):
#         self._log_args = log_args
#         self._log_results = log_results
#         self._log_enter = log_enter
#         self._log_exit = log_exit
#         self._log_path = log_path
#         self._joined = joined

#     @classmethod
#     def from_string(cls, s):
#         pass
#         return cls(...)

# def loggable(
#     log_name='*',
#     log_args=True,
#     log_results=True,
#     log_enter=True,
#     log_exit=True,
#     log_path=True,
#     joined=False,
#     short=None,
#     long=None,
#     outer_class = None,
# ):
#     """ All-purpose decorator/function for setting up logging for "loggables"

#     It is used as a decorator for functions, methods, properties and classes (it must be used for
#     classes which have decorated methods or else the methods will be "dangling"!). It is also used
#     as a regular function for so-called outer classes (i.e. classes imported from other modules
#     that still should have nice representation in logs).
#     """
#     # A class that is not in our control (like a class imported from another module) that can be
#     # an argument or result of our code, can be assigned a "short" and "long" "repr". For description
#     # see docstring of `enh_repr`. This kind of class is called "outer".
#     if outer_class is not None:
#         if short is not None:
#             # Assigning a short repr for outer class is meaningless because an outer class can
#             # never be a producer of a log (it have no decortated methods). But maybe short and long
#             # will be used somwhere else.
#             _short_class_repr[outer_class] = short
#         if long is not None:
#             _long_class_repr[outer_class] = long
#         return

#     verbosity_manager = VerbosityManager(
#         log_args = log_args,
#         log_results = log_results,
#         log_enter = log_enter,
#         log_exit = log_exit,
#         log_path = log_path,
#         joined = joined,
#     )

#     def loggable_decorator(x):
#         """ Actual decorator for "loggables"

#         It decorates functions/methods/property accesors, but also classes with any of the above.
#         """
#         global _logging_enabled, _short_class_repr, _long_class_repr
#         nonlocal log_name, verbosity_manager, short, long
#         # If it is a function or method
#         if isinstance(x, types.FunctionType):
#             # replace the wildcard `*` in the given name with the actual name of the function
#             log_name = log_name.replace('*',  x.__name__.strip('_'), 1)
#             if x.__qualname__ != x.__name__:
#                 # It is a method, so a manager is created that has parent temporarily set to `None`
#                 # it will be sorted out when the class will be decorated. It is also temporarily arrached to
#                 # `_methodtolog` property of the method. It hangs here until the class is decorated -- then all
#                 # the `_methodtolog` will be clean up. If not the logger id "dangling" -- that means that
#                 # the class of this method was not decorated as it should.
#                 x._methodtolog = LoggableFuncManager(
#                     name = log_name,
#                     parent = None,
#                     func_name = x.__name__,
#                     verbosity_manager = verbosity_manager,
#                 )
#             else:
#                 # standalone function, so module can be given for a parent
#                 lfm = LoggableFuncManager(
#                     name = log_name,
#                     parent = inspect.getmodule(x),
#                     func_name = x.__name__,
#                     verbosity_manager = verbosity_manager,
#                 )
#                 # That's it for a function, so it can be added to the registry
#                 lfm.add(on=_logging_enabled)
#         elif isinstance(x, classmethod):
#             # if it is a class method, the manager is created similarily as for a method, only the name must be digged
#             # a one step deeper
#             log_name = log_name.replace('*',  x.__func__.__name__.strip('_'), 1)
#             x._methodtolog = LoggableFuncManager(
#                 name = log_name,
#                 parent = None,
#                 func_name = x.__func__.__name__,
#                 verbosity_manager = verbosity_manager,
#             )
#         elif isinstance(x, type):
#             # Finally a class is decorated. Now we will hopefully collect all the managers that were temporarily 
#             # attached to methods `_methodtolog` properties
#             log_name = log_name.replace('*',  x.__name__.strip('_'), 1)
#             for prop_name in dir(x):
#                 # for each member of the class we try...
#                 member = x.__getattribute__(x, prop_name)
#                 if isinstance(member, property):
#                     # if it is an actual property we will have potentially three managers to sort out
#                     members = ((member.fget, 'fget'), (member.fset, 'fset'), (member.fdel, 'fdel'))
#                 else:
#                     # if it is a regular method we have just one manager
#                     members = ((member, None),)
#                 for member, subname in members:
#                     try:
#                         # Now we just try to update the manager that is hanging in the function. If it is not 
#                         # hanging there that means that we have something other than decorated method here
#                         # end the exception occurs.
#                         #
#                         # The `log_path` value is really only meaningful in the class decorator, but it is needed
#                         # in all method managers, hence it is copied here
#                         member._methodtolog.log_path = log_path
#                         # New name for the wrapper is created from the name given in the class decorator, and the name
#                         # obtained when the method was decorated
#                         member._methodtolog.name = log_name + '.' + member._methodtolog.name
#                         # the parent is finally known and can be assigned to the manager
#                         member._methodtolog.parent = x
#                         # if `subname` we are in a property
#                         if subname:
#                             # what was stored before in the manager as a name is in fact the name of property
#                             # so it has to be rewriten
#                             member._methodtolog.property_name = member._methodtolog.func_name
#                             # Function name is now one of the accesor functions: `fget`, `fset` or `fdel`
#                             member._methodtolog.func_name = subname
#                         # The method is finnaly properly set up and can be added to the registry
#                         member._methodtolog.add(on=_logging_enabled)
#                         # This temporary member is no longer needed
#                         del member._methodtolog
#                     except Exception:
#                         # It was not a decorated method (modt of the time it is not), so we do nothing
#                         pass
#             # When we decorate a class we can assign a logging "repr"s here. One is "short" and one
#             # is "long". For descriptin see docstring of `enh_repr` function.
#             if short is not None:
#                 _short_class_repr[x] = short
#             if long is not None:
#                 _long_class_repr[x] = long
#         # After decoration we return the original method/function, so the class/module has exactly the
#         # same structure as it would have it wasn't decorated at all. All the information needed is stored
#         # in the managers now. When the logging is turned on, the wrappers are created, and module/class
#         # is altered
#         return x
#     return loggable_decorator


# def just_info(*msg):
#     """ Print a log line, but respecting the graph """
#     logging.getLogger('mupf').info( "     "+_repr_tracks()+" ".join(map(str, msg)))

# def enh_repr(x, short=False):
#     """ Enhanced repr(esentation) for objects, nice in logging

#     Short version is used when the class of the object is obvious. In this case only
#     minimal identifying data should be uncluded such as `<232>`. Long version is used
#     when class is better to be noted, for example `<SomeClass i=232 good state=running>`.
#     If there is no short version, long one is used. When there is neither a standard
#     `repr()` function is used.
#     """
#     global _short_class_repr, _long_class_repr
#     if short:
#         for class_, func in _short_class_repr.items():
#             if isinstance(x, class_):
#                 return func(x)
#     for class_, func in _long_class_repr.items():
#         if isinstance(x, class_):
#             return func(x)
#     return repr(x)

# def parse_path(path):
#     result = [[[]]]
#     path += '\u0003'
#     st_obj = 0
#     st_supl = None
#     in_supl= False
#     for i, c in enumerate(path):
#         if c == '<':
#             if st_obj is not None:
#                 result[-1][-1].append(path[st_obj:i])
#                 st_obj = None
#             in_supl = True
#             st_supl = i
#             continue
#         if c == '>' and in_supl:
#             in_supl = False
#             result[-1][-1].append(path[st_supl+1:i])
#             st_supl = None
#             continue
#         if c == '.' or c == '/' or c == '\u0003':
#             if st_obj is not None:
#                 result[-1][-1].append(path[st_obj:i])
#             st_obj = i+1
#             if c == '.':
#                 result[-1].append([])
#         if c == '/' or c == '\u0003':
#             if c == '/':
#                 result.append([[]])
#             st_obj = i+1
#     return result

# def build_path(tree):
#     return "/".join([".".join([obj[0]+"".join(["<{}>".format(supl) for supl in obj[1:]]) for obj in pathpart]) for pathpart in tree])

# def _make_regexp_from_filter(f):
#     tree = parse_path(f)
#     for pathpart in tree:
#         for obj in pathpart:
#             class_ = re.split(r'(\*+)', obj[0])
#             class_.append('')
#             for i in range(len(class_)//2):
#                 class_[2*i] = re.escape(class_[2*i])
#                 star_count = len(class_[2*i+1])
#                 if star_count == 1:
#                     class_[2*i+1] = r'[^/.<]*'
#                 elif star_count == 2:
#                     class_[2*i+1] = r'[^/]*'
#                 elif star_count == 3:
#                     class_[2*i+1] = r'.*'
#                 elif star_count >= 4:
#                     raise ValueError('too many stars')
#             obj[0] = "".join(class_) + r'(?:<[^>]*>)*'
#             for supl_no in range(len(obj)-1):
#                 obj[supl_no+1] = "<" +re.escape(obj[supl_no+1]) + r'>(?:<[^>]*>)*'
#     return re.compile(build_path(tree) + r'.*')

# def _append_filter(f):
#     global _filters
#     f = f.lstrip()
#     marker = f[0]
#     f = f[1:].strip()
#     reg = _make_regexp_from_filter(f)
#     _filters.append((marker, reg))

# def _should_be_on(path):
#     global _filters
#     state = "-"
#     for f in _filters:
#         if f[1].match(path):
#             state = f[0]
#     return state

# def refresh():
#     for l in LoggableFuncManager._loggables_by_name.values():
#         if _should_be_on(l.name) == '+':
#             l.on()
#         else:
#             l.off()


# def enable(filename, fmt='[%(name)s] %(message)s',mode='w', level=logging.INFO, filters=('+ ***',)):
#     global _short_class_repr, _logging_enabled
#     logging.basicConfig(level=level)
#     hand = logging.FileHandler(filename=filename, mode=mode, encoding='utf-8')
#     hand.setFormatter(logging.Formatter(fmt))
#     logging.getLogger('').addHandler(hand)
#     for f in filters:
#         _append_filter(f)
#     refresh()
#     _logging_enabled = True
