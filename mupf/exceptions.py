class MupfError(Exception):

    def __init__(self, message=None):
        super().__init__()
        self._message = str(message)

    def __str__(self):
        return self._message

class JavaScriptError(MupfError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class CommandError(MupfError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class CommandUnknownError(CommandError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class InternalCommandError(CommandError):   # zbędne?
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ClientClosedUnexpectedly(MupfError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class ClientClosedNormally(MupfError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class UnknownConnectionError(MupfError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class DOMAttributeError(MupfError):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


by_name = {'MupfError': MupfError}
__name = None
__x = None
for __name, __x in locals().items():
    if isinstance(__x, type) and issubclass(__x, MupfError):
        by_name[__name] = __x
del __name
del __x

def create_from_result(msg):
    # msg - list [name, msg, file, line, column]
    global by_name
    if msg[0] in by_name:
        return by_name[msg[0]]("{1} [{2}:{3}:{4}]".format(*msg))
    else:
        return JavaScriptError("{0}: {1} [{2}:{3}:{4}]".format(*msg))
