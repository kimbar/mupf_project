import logging
from enum import IntEnum

from . import _tracks as tracks
from . import settings
from ._main import log_mutex

short_class_repr = {}
long_class_repr = {}



class LogWriterStyle(IntEnum):
    inner = 0
    outer = 1
    multi_line = 0
    single_line = 2


class LogWriter:

    def __init__(self, id_, printed_addr, style=LogWriterStyle.inner+LogWriterStyle.multi_line, group="Main"):
        self._group = group
        self._track = None    
        self.id_ = id_
        self._printed_addr = printed_addr
        self._linecount = 0
        self._single_line = style & LogWriterStyle.single_line
        self._inner = not (style & LogWriterStyle.outer)
        self.finished = False
    
    def write(self, text="", finish=False):
        if self._single_line:
            branch = "."
            ruler = " "+tracks.glyphs['|']+" "
            line_id = ""
        else:
            if self._linecount == 0:
                branch = 'start'
                if self._inner:
                    ruler = tracks.ligatures["<{"]+' '
                else:
                    ruler = ' '+tracks.ligatures["}>"]
                line_id = ".s"
            elif finish:
                branch = 'end'
                if self._inner:
                    ruler = ' '+tracks.ligatures["}>"]
                else:
                    ruler = tracks.ligatures["<{"]+' '
                line_id = ".f"
            else:
                branch = 'mid'
                ruler = " "+tracks.glyphs['|']+" "
                line_id = ".{}".format(self._linecount)

        with log_mutex:
            if self._track is None:
                self._track = tracks.find_free(min_=tracks.get_group_indent(self._group))
                tracks.reserve(self._track)

            line = " ".join((
                "{: <{}}".format(self._group, settings.GROUP_NAME_WIDTH)[0:settings.GROUP_NAME_WIDTH],
                tracks.write(branch, self._track, self._inner),
                '{}/{}{}'.format(self._printed_addr, self.id_, line_id),
            ))
            len_line = max(((len(line)-settings.MIN_COLUMN_WIDTH+(settings.TAB_WIDTH//2))//settings.TAB_WIDTH+1)*settings.TAB_WIDTH, 0) + settings.MIN_COLUMN_WIDTH
            line += " "*(len_line-len(line)) + ruler + ' ' + text

            logging.getLogger('mupf').info(line)

            self._linecount += 1
            if self._single_line or finish:
                tracks.free(self._track)
                self.finished = True


def just_info(*msg):
    """ Print a log line, but respecting the graph """
    logging.getLogger('mupf').info( " "*(settings.GROUP_NAME_WIDTH+1) + tracks.write() + " " + " ".join(map(str, msg)))

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
