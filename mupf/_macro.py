import io
import re
import pkg_resources
from . import _features as features_module

class MacroByteStream:
    """Very simple wrapper for byte streams providing C-like macros for JavaScript
    """
    re_macro_line = re.compile(br'^\s*//\s*#(\w*)\s*([\s\S]*?)\s*$')
    re_leading_spaces_detector = re.compile(br'^(\s*)([\s\S]*)$')
    re_number = re.compile(br'^[1-9]+[0-9]*$')
    re_argument_split = re.compile(br'\s*(==|<=|>=|!=|[|&()~+\-*<>])\s*')

    def __init__(self, stream):
        self._stream = stream
        self._labels = set()
    
    def set_from_features(self, symbols):
        for symbol in symbols:
            if symbol.state:
                self._labels.add(symbol.internal_name)
            else:
                self._labels.discard(symbol.internal_name)
        return self

    def set(self, labels):
        self._labels.update(set(labels))
        self._labels.discard('')
        return self
    
    def unset(self, labels):
        for m in labels:
            self._labels.discard(m)
        return self

    def read(self):
        curr_state = True
        if_stack = []
        result = io.BytesIO()
        while True:
            verbose = ('verbose_macros' in self._labels)
            line = self._stream.readline()
            if len(line) == 0:
                break
            m = MacroByteStream.re_macro_line.match(line)
            if m:
                if verbose:
                    result.write(line)
                directive, argument = m.groups()
                if directive == b'if':
                    # split into tokens
                    argument = re.split(MacroByteStream.re_argument_split, argument)
                    # translate from macro to Python syntax
                    argument = map(self._translate, argument)
                    # evaluate argument expression
                    predicate = eval(" ".join(argument), {}, {})
                    if_stack.append((curr_state, predicate))
                    curr_state = curr_state and predicate
                elif directive == b'else':
                    curr_state = if_stack[-1][0]
                    predicate = if_stack[-1][1]
                    curr_state = curr_state and (not predicate)
                elif directive == b'endif':
                    curr_state = if_stack.pop()[0]
                elif directive == b'print_features_state':
                    if curr_state:
                        first_label = True
                        spaces, rest = MacroByteStream.re_leading_spaces_detector.match(line).groups()
                        result.write(spaces)
                        for feature in features_module.feature_list:
                            if not first_label:
                                result.write(b', ')
                            result.write(feature.internal_name.encode('utf-8'))
                            if feature.internal_name in self._labels:
                                result.write(b':true')
                            else:
                                result.write(b':false')
                            first_label = False
                        result.write(b'\n')
                elif directive == b'define':
                    if curr_state:
                        for label in map(lambda l: l.decode('utf-8'), re.split(br'\s*,\s*', argument)):
                            m = re.match(r'^~\s*(.*)$', label)
                            if m:
                                self._labels.discard(m.group(1))
                            else:
                                self._labels.add(label)
                elif directive == b'':
                    pass
                elif directive == b'include':
                    if curr_state:
                        subfile = MacroByteStream(pkg_resources.resource_stream(__name__, argument.decode('utf-8'))).set(self._labels)
                        result.write(subfile.read())
                        if ('verbose_macros' in self._labels):
                            spaces, rest = MacroByteStream.re_leading_spaces_detector.match(line).groups()
                            result.write(spaces)
                            result.write(b'// #end-of-include-of ')
                            result.write(argument)
                            result.write(b'\n')
                        self._labels = subfile._labels
                else:
                    raise ValueError('Unknown directive `#{}`'.format(directive.decode('utf-8')))
            else:
                if curr_state:
                    result.write(line)
                elif verbose:
                    spaces, rest = MacroByteStream.re_leading_spaces_detector.match(line).groups()
                    result.write(spaces)
                    result.write(b"// ")
                    result.write(rest)
        return result.getvalue()

    def _translate(self, token):
        """
        Translates expression token from macro to Python syntax
        """
        if MacroByteStream.re_number.match(token):
            return token.decode('utf-8')
        return {
            b'~': 'not', b'&': 'and', b'|': 'or', b'(': '(',
            b')': ')', b'': '', b'+': '+', b'-': '-', b'*': '*',
            b'==': '==', b'<': '<', b'>': '>', b'<=': '<=',
            b'>=': '>=', b'!=': '!=',
        }.get(token, '1' if (token.decode('utf-8') in self._labels) else '0')
