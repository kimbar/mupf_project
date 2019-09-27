from . import _tracks as tracks
from ._main import THREAD_TAB_WIDTH, TAB_WIDTH, MIN_COLUMN_WIDTH
from enum import Enum

short_class_repr = {}
long_class_repr = {}


class LogWriterStyle(Enum):
    inner = 0
    outer = 1


class LogWriter:

    def __init__(self, id_, manager_addr, style=LogWriterStyle.inner):
        self._track = tracks.find_free()
        tracks.reserve(self._track)
        self.id_ = id_
        self._manager_addr = manager_addr
        self._linecount = 0
        if style == LogWriterStyle.inner:
            self._branch_ends = '<>'
        else:
            self._branch_ends = '><'
    
    def write(self, text, finish=False):
        if self._linecount == 0:
            branch = 'start'
            branch_end = self._branch_ends[0]
        elif finish:
            branch = 'end'
            branch_end = self._branch_ends[1]
        else:
            branch = 'mid'
            branch_end = '─'
        
        line = _make_line(
            group = '1234',
            tracks = tracks.write(branch, self._track),
            branch_end = branch_end,
            address = '{}/{}'.format(self._manager_addr, self.id_),
            ruler = ' |> ' if branch_end == '>' else '<|  ',
            details = text,
        )

        print(line)

        self._linecount += 1
        if finish:
            tracks.free(self._track)


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

def _make_line(group, tracks, branch_end, address, ruler, details):
    msg = "{0} {1}─{2} {3}".format(group, tracks, branch_end, address)
    lmsg = max(((len(msg)-MIN_COLUMN_WIDTH+(TAB_WIDTH//2))//TAB_WIDTH+1)*TAB_WIDTH, 0) + MIN_COLUMN_WIDTH
    msg += " "*(lmsg-len(msg)) + ruler + details
    return msg