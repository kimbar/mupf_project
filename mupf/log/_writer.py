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
    larr = 4
    rarr = 8


class LogWriter:

    def __init__(self, id_, printed_addr, style=LogWriterStyle.inner+LogWriterStyle.multi_line, group="Main"):
        self._group = group
        self._track = None    
        self.id_ = id_
        self._printed_addr = printed_addr
        self._linecount = 0
        self._single_line = style & LogWriterStyle.single_line
        if style & LogWriterStyle.larr:
            self._single_line_branch = '<'
        elif style & LogWriterStyle.rarr:
            self._single_line_branch = '>'
        else:
            self._single_line_branch = '.'
        self._inner = not (style & LogWriterStyle.outer)
        self.finished = False
    
    def write(self, text="", finish=False):
        if self._single_line:
            branch = self._single_line_branch
            if branch == '<':
                ruler = tracks.ligatures["<{"]+' '
            elif branch == '>':
                ruler = ' '+tracks.ligatures["}>"]
            else:
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
            
            line_elements = []
            if settings.print_group_name:
                line_elements.append("{: <{}}".format(self._group, settings.GROUP_NAME_WIDTH)[0:settings.GROUP_NAME_WIDTH])
            if settings.print_tracks:
                line_elements.append(tracks.write(branch, self._track, self._inner))
            if settings.print_address:
                line_elements.append('{}/{}{}'.format(self._printed_addr, self.id_, line_id))
            line = " ".join(line_elements)
            
            if settings.print_ruler:
                len_line = max(((len(line)-settings.MIN_COLUMN_WIDTH+(settings.TAB_WIDTH//2))//settings.TAB_WIDTH+1)*settings.TAB_WIDTH, 0) + settings.MIN_COLUMN_WIDTH
                line += " "*(len_line-len(line)) + ruler
            
            line += ' ' + text

            logging.getLogger('mupf').info(line)

            self._linecount += 1
            if self._single_line or finish:
                tracks.free(self._track)
                self.finished = True


def just_info(*msg):
    """ Print a log line, but respecting the graph """
    line = ""
    if settings.print_group_name:
        line += " "*(settings.GROUP_NAME_WIDTH+1)
    if settings.print_tracks:
        line += tracks.write()
    line += " " + " ".join(map(str, msg))
    logging.getLogger('mupf').info(line)

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
