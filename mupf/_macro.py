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

    def __init__(self, stream, substream_finder=None, code_name="", output_line_start = 1):
        self._stream = stream
        self._labels = set()
        self._substream_finder = substream_finder
        self.output_line_number = output_line_start
        self._code_name = code_name

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

    def _read(self, just_identify_line=None):
        curr_state = True
        if_stack = []
        result = io.BytesIO()
        input_line_number = 0
        verbose = ('verbose_macros' in self._labels)
        while True:
            line = self._stream.readline()
            input_line_number += 1
            if len(line) == 0:
                break
            if m := MacroByteStream.re_macro_line.match(line):
                if verbose:
                    result.write(line)
                    if adv_res := self.advance_line_number(input_line_number, just_identify_line):
                        return adv_res
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
                        if adv_res := self.advance_line_number(input_line_number, just_identify_line):
                            return adv_res
                elif directive == b'define':
                    if curr_state:
                        for label in map(lambda l: l.decode('utf-8'), re.split(br'\s*,\s*', argument)):
                            if m := re.match(r'^~\s*(.*)$', label):
                                self._labels.discard(m.group(1))
                            else:
                                self._labels.add(label)
                elif directive == b'':
                    pass
                elif directive == b'include':
                    if curr_state:
                        subfile_name = argument.decode('utf-8')
                        subfile = MacroByteStream(
                            self._substream_finder(subfile_name),
                            substream_finder=self._substream_finder,
                            code_name = subfile_name,
                            output_line_start = self.output_line_number
                            ).set(self._labels)
                        subresult = subfile._read(just_identify_line)
                        self.output_line_number = subfile.output_line_number
                        if just_identify_line is None:
                            result.write(subresult)
                        else:
                            if subresult is not None:
                                return subresult
                        if ('verbose_macros' in self._labels):
                            spaces, rest = MacroByteStream.re_leading_spaces_detector.match(line).groups()
                            result.write(spaces)
                            result.write(b'// #end-of-include-of ')
                            result.write(argument)
                            result.write(b'\n')
                            if adv_res := self.advance_line_number(input_line_number, just_identify_line):
                                return adv_res
                        self._labels = subfile._labels
                else:
                    raise ValueError('Unknown directive `#{}`'.format(directive.decode('utf-8')))
            else:
                if curr_state:
                    result.write(line)
                    if adv_res := self.advance_line_number(input_line_number, just_identify_line):
                        return adv_res
                elif verbose:
                    spaces, rest = MacroByteStream.re_leading_spaces_detector.match(line).groups()
                    result.write(spaces)
                    result.write(b"// ")
                    result.write(rest)
                    if adv_res := self.advance_line_number(input_line_number, just_identify_line):
                        return adv_res
        if just_identify_line is None:
            return result.getvalue()

    def read(self):
        return self._read(just_identify_line=None)

    def identify_line(self, line_no):
        if line_no is not None:
            return self._read(just_identify_line=line_no)

    def advance_line_number(self, input_line_number, just_identify_line):
        if just_identify_line == self.output_line_number:
            return (self._code_name, input_line_number)
        self.output_line_number += 1

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
