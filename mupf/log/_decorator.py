import inspect
import types

from . import _main as main
from . import _writer as writer
from ._manager import LogManager, LogSimpleManager
from . import settings

def loggable(
    log_addr='*',
    *,
    log_args=True,
    log_results=True,
    log_enter=True,
    log_exit=True,
    log_path=True,
    short=None,
    long=None,
    short_det = None,
    long_det = None,
    hidden=False,
):
    """ All-purpose decorator for setting up logging for "loggables"

    It is used as a decorator for functions, methods, properties and classes (it must be used for classes which have
    decorated methods or else the methods will be "dangling"!).
    """
    verbosity_settings = dict(
        log_args = log_args,
        log_results = log_results,
        log_enter = log_enter,
        log_exit = log_exit,
        log_path = log_path,
    )

    def loggable_decorator(x):
        """ Actual decorator for "loggables"

        It decorates functions/methods/property accesors, but also classes with any of the above.
        """
        nonlocal log_addr, verbosity_settings, log_path, hidden
        # If it is a function or method
        if isinstance(x, types.FunctionType):
            # replace the wildcard `*` in the given name with the actual name of the function
            log_addr = log_addr.replace('*',  x.__name__.strip('_'), 1)
            if x.__qualname__ != x.__name__:
                # It is a method, so a manager is created that has parent temporarily set to `None` it will be sorted
                # out when the class will be decorated. It is also temporarily attached to `_methodtolog` property of
                # the method. It hangs there until the class is decorated -- then all the `_methodtolog` will be cleaned
                # up. If not, the logger is "dangling" -- that means that the class of this method was not decorated as
                # it should.
                x._methodtolog = LogSimpleManager(
                    addr = log_addr,
                    log_path = log_path,
                    func_parent = None,
                    func_name = x.__name__,
                    verbosity_settings = verbosity_settings,
                    hidden = hidden,
                )
            else:
                # standalone function, so module can be given for a parent
                lfm = LogSimpleManager(
                    addr = log_addr,
                    log_path = log_path,
                    func_parent = inspect.getmodule(x),
                    func_name = x.__name__,
                    verbosity_settings = verbosity_settings,
                    hidden = hidden,
                )
                # That's it for a function, so it can be added to the registry
                lfm.add(auto_on=main._logging_enabled)
        elif isinstance(x, classmethod):
            # if it is a class method, the manager is created similarily as for a method, only the name must be digged a
            # one step deeper
            log_addr = log_addr.replace('*',  x.__func__.__name__.strip('_'), 1)
            x._methodtolog = LogSimpleManager(
                addr = log_addr,
                log_path = log_path,
                func_parent = None,
                func_name = x.__func__.__name__,
                verbosity_settings = verbosity_settings,
                hidden = hidden,
            )
        elif isinstance(x, type):
            # Finally a class is decorated.
            if issubclass(x, LogManager):
                # If it is an "aunt" class, the decorator performes a singlenton semantic That is it creates a single
                # object, and registers it in the registry
                manager = x(log_addr, log_path, hidden)
                manager.add(auto_on=main._logging_enabled)
            else:
                # It is a regular user's class Now we will hopefully collect all the managers that were temporarily
                # attached to methods `_methodtolog` properties
                log_addr = log_addr.replace('*',  x.__name__.strip('_'), 1)
                for prop_name in dir(x):
                    # for each member of the class we try...
                    # First we must find the member, and that means we must traverse the Method Resolution Order
                    for mro_class in x.__mro__:
                        try:
                            member = x.__getattribute__(mro_class, prop_name)
                        except AttributeError:
                            # The member is not in this class so we move one step in MRO.
                            pass
                        else:
                            # We found the member, so we can break from the loop
                            break
                    else:
                        # The loop was never broken.
                        # So we haven't found the member anuwhere in the `__mro__` - this should never happen, because
                        # the member was returned by `dir(x)` so it should exist somwhere. To fail safe (quaietly) we
                        # assign a `None` value to the member that will fail in expected manner down the line at
                        # `member._methodtolog.log_path`.
                        member = None
                    if isinstance(member, property):
                        # if it is an actual property we will have potentially three managers to sort out
                        members = ((member.fget, 'fget'), (member.fset, 'fset'), (member.fdel, 'fdel'))
                    else:
                        # if it is a regular method we have just one manager
                        members = ((member, None),)
                    for member, subname in members:
                        try:
                            # Now we just try to update the manager that is hanging in the function. If it is not
                            # hanging there that means that we have something other than decorated method here end the
                            # exception occurs.
                            #
                            # The `log_path` value is really only meaningful in the class decorator, but it is needed in
                            # all method managers, hence it is copied here
                            member._methodtolog.log_path = log_path
                            # New name for the wrapper is created from the name given in the class decorator, and the
                            # name obtained when the method was decorated
                            member._methodtolog.addr = log_addr + '.' + member._methodtolog.addr
                            # the parent is finally known and can be assigned to the manager
                            member._methodtolog.func_parent = x
                            # if `subname` we are in a property
                            if subname:
                                # what was stored before in the manager as a name in fact was the name of the property
                                # so it has to be rewriten
                                member._methodtolog.set_as_property_manager(member._methodtolog.func_name, subname)
                                # Function name is now one of the accesor functions: `fget`, `fset` or `fdel`
                            # The method is finnaly properly set up and can be added to the registry
                            member._methodtolog.add(auto_on=main._logging_enabled)
                            # This temporary member is no longer needed
                            del member._methodtolog
                        except Exception:
                            # It was not a decorated method (most of the time it is not), so we do nothing
                            pass
                # When we decorate a class we can assign a logging "repr"s here. One is "short" and one is "long". For
                # description see docstring of `enh_repr` function.
                loggable_class(x, short=short, long=long, short_det=short_det, long_det=long_det)
        # After decoration we return the original method/function, so the class/module has exactly the same structure as
        # it would have it wasn't decorated at all. All the information needed is stored in the managers now. When the
        # logging is turned on, the wrappers are created, and module/class is altered
        return x
    return loggable_decorator


def loggable_class(class_, *,
    short = None,
    long = None,
    short_det = None,
    long_det = None,
):
    """ Kind-of decorator for classes that are not in our control

    It is used for so-called outer classes (i.e. classes imported from other modules that still should have nice
    representation in logs).
    """
    # A class that is not in our control (like a class imported from another module) that can be an argument or result
    # of our code, can be assigned a "short" and "long" "repr". For description see docstring of `enh_repr`. This kind
    # of class is called "outer".
    if short is not None:
        # Assigning a short repr for outer class is meaningless because an outer class can never be a producer of a
        # log (it have no decortated methods). But maybe short and long will be used somwhere else.
        if not settings.deterministic_identificators:
            writer.short_class_repr[class_] = short
        elif short_det is not None:
            writer.short_class_repr[class_] = short_det
        else:
            writer.short_class_repr[class_] = lambda y: "<>"
    if long is not None:
        if not settings.deterministic_identificators:
            writer.long_class_repr[class_] = long
        elif long_det is not None:
            writer.long_class_repr[class_] = long_det
        else:
            writer.long_class_repr[class_] = lambda y: f"<obj of {str(type(y)).strip('<>')}>"
