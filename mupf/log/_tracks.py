from . import _main as main

_tracks = []
_styles = dict(
    _reference = "|,`}+-{><.",
    default =    "│┌└├┼─┤><·",
    rounded =    "│╭╰├┼─┤▶◀·",
    simple =     "|,`|+-|><*",
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


def write(branch=None, branch_track=None):
    """ Print tracks for a single line

    The line is connected to the line (branched) if `branch_track` number is given. The track number
    `branch_track` should be occupied. `branch` can have three values: `"start"` or `"end"` if the
    branch should strart or end the track, `"mid"` if the branch should only attach to a track. Any
    other value (preffered `"."`) to only mark the track for single line.
    """
    global _tracks, glyphs
    result = ""
    for n, track in enumerate(_tracks):
        if track:
            if branch:
                if n < branch_track:
                    result += glyphs["|"]
                elif n == branch_track:
                    if branch == 'start':
                        result += glyphs[","]
                    elif branch == 'end':
                        result += glyphs["`"]
                    elif branch == 'mid':
                        result += glyphs["}"]
                    else:
                        result += glyphs["."]
                elif n > branch_track:
                    result += glyphs["+"]
            else:
                result += glyphs["|"]
        else:
            if branch:
                if n < branch_track:
                    result += " "
                elif n == branch_track:
                    result += "?"
                elif n > branch_track:
                    result += glyphs["-"]
            else:
                result += " "
    return result
