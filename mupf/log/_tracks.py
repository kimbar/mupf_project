from . import _main as main
from . import settings

_tracks = []
_styles = dict(
    _reference = "|,`}+-{><.T^t",
    default =    "│┌└├┼─┤><·┐┘─",
    rounded =    "│╭╰├┼─┤><·╮╯─",
    simple =     "|,`|+-|><*,'-",
)
glyphs = {}
ligatures = {}

def set_style(characters):
    global ligatures, glyphs, _styles
    if len(characters) != len(_styles['_reference']):
        raise ValueError('Wrong length of character set')
    glyphs = {_styles['_reference'][i]:characters[i] for i in range(len(characters))}
    ligatures = {lig: "".join(characters[_styles['_reference'].index(ch)] for ch in lig) for lig in (
        "<-", "->", "<{", "}>"
    )}

set_style(_styles['default'])


def is_occupied(n):
    """ Check if track is already taken """
    global _tracks
    if n >= len(_tracks):
        return False
    else:
        return _tracks[n]

def reserve(n):
    """ Reserve a track w/o checking """
    global _tracks
    if n >= len(_tracks):
        _tracks += [False]*(n-len(_tracks)+1)
    _tracks[n] = True

def free(n):
    """ Free a track w/o checking """
    global _tracks
    _tracks[n] = False
    while not _tracks[-1]:
        _tracks.pop()
        if len(_tracks) == 0:
            break

def find_free(min_=0):
    """ Find a free track, but at least `min_` one """
    while is_occupied(min_):
        min_ += 1
    return min_


def write(branch=None, branch_track=None, inner=True, connect_to=None):
    """ Print tracks for a single line

    The line is connected to the line (branched) if `branch_track` number is given. The track number
    `branch_track` should be occupied. `branch` can have three values: `"start"` or `"end"` if the
    branch should start or end the track, `"mid"` if the branch should only attach to a track. Any
    other value to only mark the track for single line. When the single line is used, the `"<"`
    draws left pointing arrow after the track mark; `">"` draws right pointing arrow; and `"."`
    draws no arrow (only the track mark).
    """
    global _tracks, glyphs
    if inner:
        result = " "
    else:
        if branch == 'start':
            result = glyphs[">"]
        elif branch == 'end':
            result = glyphs["<"]
        else:
            result = glyphs["-"]

    for n, track in enumerate(_tracks):
        if track:
            if branch:
                if n < branch_track:
                    if n == connect_to:
                        result += glyphs["}"]
                    elif inner or branch == 'mid':
                        result += glyphs["|"]
                    else:
                        result += glyphs["+"]
                elif n == branch_track:
                    if branch == 'start':
                        if inner:
                            result += glyphs[","]
                        else:
                            result += glyphs["T"]
                    elif branch == 'end':
                        if inner:
                            result += glyphs["`"]
                        else:
                            result += glyphs["^"]
                    elif branch == 'mid':
                        if inner:
                            result += glyphs["}"]
                        else:
                            result += glyphs["|"]
                    else:
                        result += glyphs["."]
                elif n > branch_track:
                    result += glyphs["+"]
            else:
                result += glyphs["|"]
        else:
            if branch:
                if n < branch_track:
                    if inner or branch == 'mid':
                        result += " "
                    else:
                        result += glyphs["-"]
                elif n == branch_track:
                    result += "?"
                elif n > branch_track:
                    result += glyphs["-"]
            else:
                result += " "
    if inner:
        if branch:
            if branch == 'start' or branch == '<':
                result += ligatures['<-']
            elif branch == 'end' or branch == '>':
                result += ligatures['->']
            else:
                result += glyphs["-"]+glyphs["-"]
        else:
            result += "  "
    else:
        if branch == '<':
            result += ligatures['<-']
        elif branch == '>':
            result += ligatures['->']
        else:
            result += glyphs["-"]+glyphs["-"]
    return result+":"


_groups_indent = {}
_last_group_indent = 0

def get_group_indent(group):
    global _groups_indent, _last_group_indent
    if group not in _groups_indent:
        if len(_groups_indent) > 0:
            _last_group_indent += settings.GROUP_WIDTH
        _groups_indent[group] = _last_group_indent
    return _groups_indent[group]


_stack_frames_by_track = {}
_tracks_by_stack_frames = {}

def register_stack_frame(frame, track):
    global _stack_frames_by_track, _tracks_by_stack_frames
    _stack_frames_by_track[track] = frame
    _tracks_by_stack_frames[frame] = track

def deregister_stack_frame(track):
    global _stack_frames_by_track, _tracks_by_stack_frames
    if track in _stack_frames_by_track:
        frame = _stack_frames_by_track[track]
        del _tracks_by_stack_frames[frame]
        del _stack_frames_by_track[track]

def get_track_by_stack_frame(frame):
    global _tracks_by_stack_frames
    return _tracks_by_stack_frames.get(frame, None)
