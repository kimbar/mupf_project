from . import _main as main

_tracks = []

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

    The line is connected to the line (branched) if `branch` number is given. The track number
    `branch` should be occupied. `branch_track` can have three values: `"start"` or `"end"` if the
    branch should strart or end the track, and any other value (preffered `"mid"`) if the branch
    should only attach to a track.
    """
    global _tracks
    result = ""
    for n, track in enumerate(_tracks):
        if track:
            if branch:
                if n < branch_track:
                    result += "│"
                elif n == branch_track:
                    if branch == 'start':
                        result += "╭" if main.rounded_graph_corners else "┌"
                    elif branch == 'end':
                        result += "╰" if main.rounded_graph_corners else "└"
                    else:
                        result += "├"
                elif n > branch_track:
                    result += "┼"
            else:
                result += "│"
        else:
            if branch:
                if n < branch_track:
                    result += " "
                elif n == branch_track:
                    result += "?"
                elif n > branch_track:
                    result += "─"
            else:
                result += " "
    return result
