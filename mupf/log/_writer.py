

short_class_repr = {}
long_class_repr = {}

class LogWriter:

    def __init__(self, id_):
        self.id_ = id_
    
    def write(self, text, finish=False):
        print(text, '' if finish else '...')


def enh_repr(x, short=False):
    """ Enhanced repr(esentation) for objects, nice in logging

    Short version is used when the class of the object is obvious. In this case only
    minimal identifying data should be uncluded such as `<232>`. Long version is used
    when class is better to be noted, for example `<SomeClass i=232 good state=running>`.
    If there is no short version, long one is used. When there is neither a standard
    `repr()` function is used.
    """
    global short_class_repr, long_class_repr
    if short:
        for class_, func in short_class_repr.items():
            if isinstance(x, class_):
                return func(x)
    for class_, func in long_class_repr.items():
        if isinstance(x, class_):
            return func(x)
    return repr(x)