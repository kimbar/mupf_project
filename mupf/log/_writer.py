from . import _tracks as tracks
from ._main import THREAD_TAB_WIDTH, TAB_WIDTH, MIN_COLUMN_WIDTH
from enum import IntEnum

short_class_repr = {}
long_class_repr = {}


class LogWriterStyle(IntEnum):
    inner = 0
    outer = 1
    multi_line = 0
    single_line = 2


class LogWriter:

    def __init__(self, id_, printed_addr, style=LogWriterStyle.inner):
        self._track = tracks.find_free()
        tracks.reserve(self._track)    
        self.id_ = id_
        self._printed_addr = printed_addr
        self._linecount = 0
        self._single_line = style & LogWriterStyle.single_line
        # │ ╭ ╰ ├ ┼ ─ ┤ > <
        # 0 1 2 3 4 5 6 7 8
        if style & LogWriterStyle.outer:
            self._branch_ends = (tracks.ligatures["->"], tracks.ligatures["<-"])
        else:
            self._branch_ends = (tracks.ligatures["<-"], tracks.ligatures["->"])
    
    def write(self, text=None, finish=False):
        if self._single_line:
            branch = "."
            branch_end = self._branch_ends[1 if finish else 0]
        else:
            if self._linecount == 0:
                branch = 'start'
                branch_end = self._branch_ends[0]
            elif finish:
                branch = 'end'
                branch_end = self._branch_ends[1]
            else:
                branch = 'mid'
                branch_end = tracks.glyphs["-"]+tracks.glyphs["-"]
        
        line = _make_line(
            group = '1234',
            tracks = tracks.write(branch, self._track),
            branch_end = branch_end,
            address = '{}/{}'.format(self._printed_addr, self.id_),
            ruler = (' '+tracks.ligatures["}>"]) if branch_end == tracks.ligatures['->'] else (tracks.ligatures["<{"]+' '),
            details = text,
        )
        print(line)

        self._linecount += 1
        if self._single_line or finish:
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
    return repr(x).lstrip('<').rstrip('>')

def _make_line(group, tracks, branch_end, address, ruler, details):
    msg = "{0} {1}{2} {3}".format(group, tracks, branch_end, address)
    if details is None:
        details = ""
    lmsg = max(((len(msg)-MIN_COLUMN_WIDTH+(TAB_WIDTH//2))//TAB_WIDTH+1)*TAB_WIDTH, 0) + MIN_COLUMN_WIDTH
    msg += " "*(lmsg-len(msg)) + ruler + ' ' + details
    return msg