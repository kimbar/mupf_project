import io
from enum import Enum
from . import _symbols as S

class OptPolicy(Enum):
    none = 0
    non_zero_count = 1
    always_count = 2


class JsonElement(Enum):
    Object = 0          # JSON object `{"key1":3, "key2":"value"}`
    Array = 1           # JSON array `[1, 2, "blah", 7]`
    String = 2          # JSON string `"a string!"`
    Number = 3          # JSON number `123.56`
    Bool = 4            # JSON bool `true`
    Null = 5            # JSON null value `null`
    Unknown = 6         # Value unknown - it's unknown how to encode it
    Autonomous = 7      # object that provides `.enh_json_esc()` method
    EscapeBlock = 8     # a JSON array, but as an escape `["~@", 340]`
    DirectJson = 9      # a `byte` stream directly put into JSON (potentially malformed!)


def test_element_type(x) -> JsonElement:
    if hasattr(x, 'keys') and callable(x.keys) and hasattr(x, '__getitem__'):
        return JsonElement.Object
    if isinstance(x, str):
        return JsonElement.String
    if hasattr(x, '__len__') and hasattr(x, '__getitem__'):
        return JsonElement.Array
    if isinstance(x, bool):
        return JsonElement.Bool
    if x is None:
        return JsonElement.Null
    if isinstance(x, (int, float)):
        return JsonElement.Number
    if isinstance(x, IJsonEsc) or (isinstance(x, type) and issubclass(x, IJsonEsc)):
        return JsonElement.Autonomous

    return JsonElement.Unknown

class EnhancedBlock:

    def __init__(self, value, explicit=False, opt=OptPolicy.non_zero_count):
        self.explicit = explicit
        self._opt = opt
        self.value = value
        self._start_pos = None
        self._addr = []
        self._esc_count = 0
        self._values_count = 0
        self._esc_addreses = []
        self._esc_positions = []

    def start(self, stream):
        self._start_pos = stream.tell()
        stream.write(b'["~",')

    def end(self, stream):
        if self._opt == OptPolicy.none:
            if self.explicit or self._esc_count > 0:
                stream.write(b',{}]')
                return True
            else:
                stream.seek(self._start_pos)
                stream.write(b'\x00\x00\x00\x00\x00')
                stream.seek(0,2)   # SEEK_END == 2
                return False
        elif self._opt == OptPolicy.non_zero_count:
            if self.explicit or self._esc_count > 0:
                stream.write(b',{"c":')
                stream.write(str(self._esc_count).encode())
                stream.write(b'}]')
                return True
            else:
                stream.seek(self._start_pos)
                stream.write(b'\x00\x00\x00\x00\x00')
                stream.seek(0,2)   # SEEK_END == 2
                return False
        elif self._opt == OptPolicy.always_count:
            stream.write(b',{"c":')
            stream.write(str(self._esc_count).encode())
            stream.write(b'}]')
            return True
        else:
            raise ValueError(f'Unknown optimalization policy {repr(self._opt)}')

    def esc_here(self, handler, stack, stream):
        self.nested_eb_ends_here()
        stack.append([1, True, handler])  # mode == 1 == 'esc'
        stream.write(b'["~')
        if isinstance(handler, str):
            handler = handler.encode('utf-8')
        stream.write(handler)
        stream.write(b'",')

    def nested_eb_ends_here(self):
        self._esc_count += 1
        self._esc_addreses.append(self._addr.copy())
        self._esc_positions.append(self._values_count)

    def encoded_value_here(self):
        self._values_count += 1

    def addr_change(self, last):
        self._addr[-1] = last

    def addr_append(self, new):
        self._addr.append(new)

    def addr_pop(self):
        self._addr.pop()

# Lookup table of arbitrary bytes into JSON-compatibile string representation
_string_esc = [
    b'\\u0000', b'\\u0001', b'\\u0002', b'\\u0003', b'\\u0004', b'\\u0005', b'\\u0006', b'\\u0007',
    b'\\\x62',  b'\\\x74',  b'\\\x6E',  b'\\u000B', b'\\\x66',  b'\\\x72',  b'\\u000E', b'\\u000F',
    b'\\u0010', b'\\u0011', b'\\u0012', b'\\u0013', b'\\u0014', b'\\u0015', b'\\u0016', b'\\u0017',
    b'\\u0018', b'\\u0019', b'\\u001A', b'\\u001B', b'\\u001C', b'\\u001D', b'\\u001E', b'\\u001F',
    b'\x20',    b'\x21',    b'\\\x22',  b'\x23',    b'\x24',    b'\x25',    b'\x26',    b'\x27',
    b'\x28',    b'\x29',    b'\x2A',    b'\x2B',    b'\x2C',    b'\x2D',    b'\x2E',    b'\x2F',
    b'\x30',    b'\x31',    b'\x32',    b'\x33',    b'\x34',    b'\x35',    b'\x36',    b'\x37',
    b'\x38',    b'\x39',    b'\x3A',    b'\x3B',    b'\x3C',    b'\x3D',    b'\x3E',    b'\x3F',
    b'\x40',    b'\x41',    b'\x42',    b'\x43',    b'\x44',    b'\x45',    b'\x46',    b'\x47',
    b'\x48',    b'\x49',    b'\x4A',    b'\x4B',    b'\x4C',    b'\x4D',    b'\x4E',    b'\x4F',
    b'\x50',    b'\x51',    b'\x52',    b'\x53',    b'\x54',    b'\x55',    b'\x56',    b'\x57',
    b'\x58',    b'\x59',    b'\x5A',    b'\x5B',    b'\\\x5C',  b'\x5D',    b'\x5E',    b'\x5F',
    b'\x60',    b'\x61',    b'\x62',    b'\x63',    b'\x64',    b'\x65',    b'\x66',    b'\x67',
    b'\x68',    b'\x69',    b'\x6A',    b'\x6B',    b'\x6C',    b'\x6D',    b'\x6E',    b'\x6F',
    b'\x70',    b'\x71',    b'\x72',    b'\x73',    b'\x74',    b'\x75',    b'\x76',    b'\x77',
    b'\x78',    b'\x79',    b'\x7A',    b'\x7B',    b'\x7C',    b'\x7D',    b'\x7E',    b'\x7F',
    b'\x80',    b'\x81',    b'\x82',    b'\x83',    b'\x84',    b'\x85',    b'\x86',    b'\x87',
    b'\x88',    b'\x89',    b'\x8A',    b'\x8B',    b'\x8C',    b'\x8D',    b'\x8E',    b'\x8F',
    b'\x90',    b'\x91',    b'\x92',    b'\x93',    b'\x94',    b'\x95',    b'\x96',    b'\x97',
    b'\x98',    b'\x99',    b'\x9A',    b'\x9B',    b'\x9C',    b'\x9D',    b'\x9E',    b'\x9F',
    b'\xA0',    b'\xA1',    b'\xA2',    b'\xA3',    b'\xA4',    b'\xA5',    b'\xA6',    b'\xA7',
    b'\xA8',    b'\xA9',    b'\xAA',    b'\xAB',    b'\xAC',    b'\xAD',    b'\xAE',    b'\xAF',
    b'\xB0',    b'\xB1',    b'\xB2',    b'\xB3',    b'\xB4',    b'\xB5',    b'\xB6',    b'\xB7',
    b'\xB8',    b'\xB9',    b'\xBA',    b'\xBB',    b'\xBC',    b'\xBD',    b'\xBE',    b'\xBF',
    b'\xC0',    b'\xC1',    b'\xC2',    b'\xC3',    b'\xC4',    b'\xC5',    b'\xC6',    b'\xC7',
    b'\xC8',    b'\xC9',    b'\xCA',    b'\xCB',    b'\xCC',    b'\xCD',    b'\xCE',    b'\xCF',
    b'\xD0',    b'\xD1',    b'\xD2',    b'\xD3',    b'\xD4',    b'\xD5',    b'\xD6',    b'\xD7',
    b'\xD8',    b'\xD9',    b'\xDA',    b'\xDB',    b'\xDC',    b'\xDD',    b'\xDE',    b'\xDF',
    b'\xE0',    b'\xE1',    b'\xE2',    b'\xE3',    b'\xE4',    b'\xE5',    b'\xE6',    b'\xE7',
    b'\xE8',    b'\xE9',    b'\xEA',    b'\xEB',    b'\xEC',    b'\xED',    b'\xEE',    b'\xEF',
    b'\xF0',    b'\xF1',    b'\xF2',    b'\xF3',    b'\xF4',    b'\xF5',    b'\xF6',    b'\xF7',
    b'\xF8',    b'\xF9',    b'\xFA',    b'\xFB',    b'\xFC',    b'\xFD',    b'\xFE',    b'\xFF',
]

def _encode_string(s, stream):
    global _string_esc
    stream.write(b'"')
    for i in str(s).encode('utf-8'):
        stream.write(_string_esc[i])
    stream.write(b'"')

#  stack's frame first element is mode:
#  mode mnemonic = "enh" | "esc" | "arr" | "obj" | "ufa"
#  magic number =    0   |   1   |   2   |   3   |   4
#
#  "enh" - Enhanced mode block
#  "esc" - Escape sequence
#  "arr" - Array (list, tuple)
#  "obj" - Object (dict)
#  "ufa" - unfenced array (array without `[` and `]`)
#
#  Frames put on the stack have one of the forms:
#
#  [0, <previous enhanced block object>] -- frame for enhancement
#    <previous enhanced block object> -- class `EnhancedBlock` object if nested, otherwise `None`
#
#  [1, <first pass>, <handler>] -- frame for escaping
#    <first pass> -- `bool` showing if the frame is passed for the first time (encode the value) or
#      second time (close the escape structure and clean up)
#    <handler> -- the name of the handler being encoded, used to properly service the escape structure
#
#  [<mode == 2|3|4>, <container>, <key iterator>, <first pass>] -- frame for array, object and "unfenced array"
#    <container> -- the container being encoded
#    <key iterator> -- iterator generating subsequent keys for the container's `__getitem__()`
#    <first pass> -- `bool` for puting a `,` or not.

def encode(value, *, escape=test_element_type):
    result = io.BytesIO()
    current_value = value
    stack = []
    current_enhanced_block = None
    #
    # This loop is never broken -- when the stack is empty, we jump out of this function
    # altogether
    while True:
        if isinstance(current_value, EnhancedBlock):
            # `EnhancedBlock` object act just as a wrapper for a value, but its occurence
            # in the encoded structure switches on the enhanced mode, where atypical objects
            # can be encoded with escape structures.
            stack.append([0, current_enhanced_block]) # mode == 0 == 'enh'
            current_enhanced_block = current_value
            current_enhanced_block.start(result)
            current_value = current_value.value
            # important here: if enhanced blocks are nested, the inner must be encoded
            # explicitely with "~!" handler
        #
        # Here we check the "type" of the value, and then act acordingly -- that is
        # we encode the value, encode some separators and/or biuld the stack. The stack
        # allows us to get deeper into the tree structure of JSON
        #
        # First we ask a function `escape()` (provided by the `Client`) what it thinks about
        # the value. It returns either a tuple or an enum value of `JsonElement` type or `None`
        esc_result = escape(current_value)
        # If the `escape` returned `JsonElement.Unknown` the value
        # must be tested for the type of JSON element.
        current_type = JsonElement.EscapeBlock
        if esc_result == JsonElement.Unknown or esc_result is None:
            current_type = test_element_type(current_value)
        elif isinstance(esc_result, JsonElement):
            current_type = esc_result
        #
        if current_type == JsonElement.Autonomous:
            try:
                esc_result = current_value.enh_json_esc()
            except Exception:
                esc_result = IJsonEsc.enh_json_esc(current_value)
            current_type = JsonElement.EscapeBlock
        #
        if current_type == JsonElement.EscapeBlock:
            if not (isinstance(esc_result, tuple) and len(esc_result)>0 and isinstance(esc_result[0], (str, bytes))):
                current_type = JsonElement.DirectJson
                current_value = b'["~?","IllformedEscTupleError"]'
        #
        # Now the "type" is known, and we can proceed acordingly. Note that
        # `JsonElement.Autonomous` type is never passed on, becouse it is casted
        # to `JsonElement.EscapeBlock`
        if current_type == JsonElement.Object:
            keys = current_value.keys()
            stack.append([3, current_value, (k for k in keys), True])    # mode == 3 == 'obj'
            result.write(b'{')
            if current_enhanced_block:
                current_enhanced_block.addr_append(None)
        elif current_type == JsonElement.String:
            _encode_string(current_value, result)
        elif current_type == JsonElement.Array:
            length = len(current_value)
            if (    current_enhanced_block    # this long condition checks if value must be escaped, but...
                and length > 1
                and isinstance(current_value[0], str)
                and current_value[0][:1] == '~'
                # ... we don't want to escape it if we already in escape structure!
                and not (  # note: if `current_enhanced_block` exists there must be something on the stack
                        len(stack) > 1
                    and stack[-2][0] == 1      # mode == 1 == 'esc'
                    and stack[-2][2] == b'~'
                )
            ):
                current_enhanced_block.esc_here(b'~', stack, result)
                # We need to wrap the current value in tuple.
                # We will put an escape frame on the stack -- it will encode the array normally,
                # but an escape sequence can encode muliple parameters (with "ufa" mode)
                # so we need to wrap the list so it will be treated as a single parameter.
                #
                current_value = (current_value,)
            else:    # Not in enhanced mode or no collision or inside the "~~" escape -- start regular array
                stack.append([2, current_value, (n for n in range(length)), True])    # mode == 2 == 'arr'
                result.write(b'[')
                if current_enhanced_block:
                    current_enhanced_block.addr_append(None)
        elif current_type == JsonElement.Bool:
            result.write(b'true' if current_value else b'false')
        elif current_type == JsonElement.Null:
            result.write(b'null')
        elif current_type == JsonElement.Number:
            result.write(str(current_value).encode())
        elif current_type == JsonElement.EscapeBlock:
            if current_enhanced_block:
                # The `escape` or the autonomous object returned a tuple. The
                # first element of this tuple is the name of the handler for
                # escape block.
                current_enhanced_block.esc_here(esc_result[0], stack, result)
                # Arguments of the escape structure (if any) will be encoded after the name
                # of the handler in "ufa" mode.
                current_value = esc_result[1:]
            else:
                result.write(b'["~?","NoEnhJSONBlockError","ENHANCED JSON ENCODING NOT STARTED"]')
        elif current_type == JsonElement.Unknown:
            # Despite the effort it is still clasiffied as `JsonElement.Unknown`
            result.write(b'["~?","UnknownObjectError"]')
        elif current_type == JsonElement.DirectJson:
            if not isinstance(current_value, bytes):
                current_value = b'["~?","BadDirectJsonValueError"]'
            result.write(current_value)
        else:
            # That should never be written. Someone subclassed `JsonElement`?
            result.write(b'["~?","UnknownJsonElementError"]')
        #
        # Here we inform the enhanced block that a normal value has been encoded.
        # This is done to give the EB data on the position of escape structures
        # inside all of the data, so it could choose apropriate optimization
        # strategy.
        if current_enhanced_block and (stack[-1][0] != 1 or stack[-1][1]):
            current_enhanced_block.encoded_value_here()
        #
        # In this part we are acting acordingly to the content of the stack. Top element
        # of the stack will (a) tell us what to do in the next iteration, or (b) the top
        # element should be removed from the stack. The loop is repeated until (a) occurs or
        # the stack is empty. If the stack is empty the encoding is done.
        while True:
            if stack:    # Process top element of the stack
                if stack[-1][0] == 0:      # mode: 'enh'
                    # End of enhanced mode, we revert to previous enhancement block
                    # (which can be `None`) and remove this frame from the stack
                    nested_explicit = current_enhanced_block.end(result)
                    current_enhanced_block = stack[-1][1]
                    if current_enhanced_block and nested_explicit:
                        # if it was nested EB we need to inform the parent that child has ended
                        current_enhanced_block.nested_eb_ends_here()
                    stack.pop()
                    continue
                elif stack[-1][0] == 1:    # mode: 'esc'
                    # handler-escape structure -- this is done twice
                    if stack[-1][1]:
                        # First pass: encode the handler-escape structure handler argument (and prepare to second pass)
                        if current_enhanced_block:
                            current_enhanced_block.addr_append(None)
                        stack[-1][1] = False    # Not first pass anymore
                        stack.append([4, current_value, (n for n in range(len(current_value))), True])    # mode == 4 == 'ufa'
                        continue
                    else:
                        # Second pass: end of handler-escape structure, remove frame from stack
                        result.write(b']')
                        if current_enhanced_block:
                            current_enhanced_block.addr_pop()
                        stack.pop()
                        continue
                else:                      # mode: 'arr' | 'obj' | 'ufa' -- dict-like or list-like elements
                    try:                     # get new element key (hashable for dict, and int for list)
                        key = next(stack[-1][2])
                    except StopIteration:    # no more keys -- end the structure, remove frame from the stack
                        if stack[-1][0] == 3: # mode == 3 == 'obj'
                            result.write(b'}')
                        elif stack[-1][0] == 2:
                            result.write(b']')
                        if current_enhanced_block and stack[-1][0]!=4:
                            current_enhanced_block.addr_pop()
                        stack.pop()
                        continue
                    else:                    # next key
                        if stack[-1][3]:    # is it the first element of this container?
                            stack[-1][3] = False   # Next element won't be the first one
                        else:
                            result.write(b',')     # put the separator
                        if current_enhanced_block:
                            # the key in object is always a string in JSON, even if it is an int in Python
                            # so the `if` below is done to distingish arrays indices from object keys
                            # (by their type: str - object, int - array)
                            current_enhanced_block.addr_change((key+(1 if (stack[-1][0]==4) else 0)) if (stack[-1][0]==2 or stack[-1][0]==4) else str(key))
                        if stack[-1][0] == 3: # mode == 3 == 'obj'
                            # Print the key for the object structure
                            _encode_string(key, result)
                            result.write(b':')
                        # Now stack is in cleaned condition, but still not empty
                        # We can obtain current structure element that need to be encoded now:
                        current_value = stack[-1][1][key]
                        break
            else:        # The stack is now empty -- the work is done
                return result.getvalue().translate(None, delete=b'\x00').decode('utf-8')


class IJsonEsc:
    @classmethod
    def enh_json_esc(cls, x=None):
        if x is None:
            x = cls
        return b"?", "NoEnhJSONAPIError", repr(x)

class undefined(IJsonEsc):
    @classmethod
    def enh_json_esc(cls):
        return b"S", "undefined"

class NaN(IJsonEsc):
    @classmethod
    def enh_json_esc(cls):
        return b"S", "NaN"

class Infinity(IJsonEsc):
    @classmethod
    def enh_json_esc(cls):
        return b'S', "Infinity"


def decode(value, esc_decoders):
    if isinstance(value, list) and isinstance(value[0], str) and value[0] == "~":
        return _decode_req(value[1], esc_decoders)
    return value

def _decode_req(value, esc_decoders):
    if isinstance(value, list):
        if len(value) > 1 and isinstance(value[0], str) and value[0][:1] == "~":
            if  value[0] == "~-":
                return value[1]
            elif value[0] == "~~":
                return [_decode_req(x, esc_decoders) for x in value[1]]
            else:
                return esc_decoders[value[0]](*[_decode_req(x, esc_decoders) for x in value[1:]])
        else:
            return [_decode_req(x, esc_decoders) for x in value]
    elif isinstance(value, dict):
        return {k: _decode_req(v, esc_decoders) for k,v in value.items()}
    else:
        return value
