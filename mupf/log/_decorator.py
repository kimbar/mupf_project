import types
import inspect

from . import _verbosity as verbosity
from ._verbosity import VerbosityManager
from ._manager import LoggableFuncManager
from . import _main as main

def loggable(
    log_name='*',
    log_args=True,
    log_results=True,
    log_enter=True,
    log_exit=True,
    log_path=True,
    joined=False,
    short=None,
    long=None,
    outer_class = None,
):
    """ All-purpose decorator/function for setting up logging for "loggables"

    It is used as a decorator for functions, methods, properties and classes (it must be used for
    classes which have decorated methods or else the methods will be "dangling"!). It is also used
    as a regular function for so-called outer classes (i.e. classes imported from other modules
    that still should have nice representation in logs).
    """
    # A class that is not in our control (like a class imported from another module) that can be
    # an argument or result of our code, can be assigned a "short" and "long" "repr". For description
    # see docstring of `enh_repr`. This kind of class is called "outer".
    if outer_class is not None:
        if short is not None:
            # Assigning a short repr for outer class is meaningless because an outer class can
            # never be a producer of a log (it have no decortated methods). But maybe short and long
            # will be used somwhere else.
            verbosity.short_class_repr[outer_class] = short
        if long is not None:
            verbosity.long_class_repr[outer_class] = long
        return

    verbosity_manager = VerbosityManager(
        log_args = log_args,
        log_results = log_results,
        log_enter = log_enter,
        log_exit = log_exit,
        log_path = log_path,
        joined = joined,
    )

    def loggable_decorator(x):
        """ Actual decorator for "loggables"

        It decorates functions/methods/property accesors, but also classes with any of the above.
        """
        nonlocal log_name, verbosity_manager, short, long
        # If it is a function or method
        if isinstance(x, types.FunctionType):
            # replace the wildcard `*` in the given name with the actual name of the function
            log_name = log_name.replace('*',  x.__name__.strip('_'), 1)
            if x.__qualname__ != x.__name__:
                # It is a method, so a manager is created that has parent temporarily set to `None`
                # it will be sorted out when the class will be decorated. It is also temporarily arrached to
                # `_methodtolog` property of the method. It hangs here until the class is decorated -- then all
                # the `_methodtolog` will be clean up. If not the logger id "dangling" -- that means that
                # the class of this method was not decorated as it should.
                x._methodtolog = LoggableFuncManager(
                    name = log_name,
                    parent = None,
                    func_name = x.__name__,
                    verbosity_manager = verbosity_manager,
                )
            else:
                # standalone function, so module can be given for a parent
                lfm = LoggableFuncManager(
                    name = log_name,
                    parent = inspect.getmodule(x),
                    func_name = x.__name__,
                    verbosity_manager = verbosity_manager,
                )
                # That's it for a function, so it can be added to the registry
                lfm.add(on=main._logging_enabled)
        elif isinstance(x, classmethod):
            # if it is a class method, the manager is created similarily as for a method, only the name must be digged
            # a one step deeper
            log_name = log_name.replace('*',  x.__func__.__name__.strip('_'), 1)
            x._methodtolog = LoggableFuncManager(
                name = log_name,
                parent = None,
                func_name = x.__func__.__name__,
                verbosity_manager = verbosity_manager,
            )
        elif isinstance(x, type):
            # Finally a class is decorated. Now we will hopefully collect all the managers that were temporarily 
            # attached to methods `_methodtolog` properties
            log_name = log_name.replace('*',  x.__name__.strip('_'), 1)
            for prop_name in dir(x):
                # for each member of the class we try...
                member = x.__getattribute__(x, prop_name)
                if isinstance(member, property):
                    # if it is an actual property we will have potentially three managers to sort out
                    members = ((member.fget, 'fget'), (member.fset, 'fset'), (member.fdel, 'fdel'))
                else:
                    # if it is a regular method we have just one manager
                    members = ((member, None),)
                for member, subname in members:
                    try:
                        # Now we just try to update the manager that is hanging in the function. If it is not 
                        # hanging there that means that we have something other than decorated method here
                        # end the exception occurs.
                        #
                        # The `log_path` value is really only meaningful in the class decorator, but it is needed
                        # in all method managers, hence it is copied here
                        member._methodtolog.log_path = log_path
                        # New name for the wrapper is created from the name given in the class decorator, and the name
                        # obtained when the method was decorated
                        member._methodtolog.name = log_name + '.' + member._methodtolog.name
                        # the parent is finally known and can be assigned to the manager
                        member._methodtolog.parent = x
                        # if `subname` we are in a property
                        if subname:
                            # what was stored before in the manager as a name is in fact the name of property
                            # so it has to be rewriten
                            member._methodtolog.property_name = member._methodtolog.func_name
                            # Function name is now one of the accesor functions: `fget`, `fset` or `fdel`
                            member._methodtolog.func_name = subname
                        # The method is finnaly properly set up and can be added to the registry
                        member._methodtolog.add(on=main._logging_enabled)
                        # This temporary member is no longer needed
                        del member._methodtolog
                    except Exception:
                        # It was not a decorated method (modt of the time it is not), so we do nothing
                        pass
            # When we decorate a class we can assign a logging "repr"s here. One is "short" and one
            # is "long". For descriptin see docstring of `enh_repr` function.
            if short is not None:
                verbosity.short_class_repr[x] = short
            if long is not None:
                verbosity.long_class_repr[x] = long
        # After decoration we return the original method/function, so the class/module has exactly the
        # same structure as it would have it wasn't decorated at all. All the information needed is stored
        # in the managers now. When the logging is turned on, the wrappers are created, and module/class
        # is altered
        return x
    return loggable_decorator