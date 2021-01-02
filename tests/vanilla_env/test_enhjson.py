"""Test suite for the `_enhjson.py` module
"""
import unittest
from mupf import _enhjson as j


class U:
    def __init__(self, x):
        self.x = x
    def nonstandard_esc_method_1(self):
        return "u", self.x

class K:
    def nonstandard_esc_method_2(self):
        return "@", 650

class KK(j.IJsonEsc):
    def enh_json_esc(self):
        return "@", 650, 340

def escape(x):
    if isinstance(x, U):
        return x.nonstandard_esc_method_1()
    if isinstance(x, K):
        return x.nonstandard_esc_method_2()

def escape_lazy(x):
    if j.test_element_type(x) == j.JsonElement.Unknown:
        return j.JsonElement.Autonomous

def bad_escape(x):
    if x==3:
        return "it's not a tuple at all - it's a string"
    if x==1000:
        return "very long "*100    # This should be truncated from 1000 to 128 characters


class EnhJSON(unittest.TestCase):

    def setUp(self):
        print(self.shortDescription())

    def test_basic(self):
        "enhjson: Simple input -> Encoded string"

        a = j.encode("basic")
        self.assertEqual(a, '"basic"')

    def test_complex(self):
        "enhjson: Complex inputs -> Encoded strings"

        a = j.encode(j.EnhancedBlock([7, "a", j.EnhancedBlock([3,5,6])]))
        self.assertEqual(a, '[7,"a",[3,5,6]]')
        b = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[K(), "prop", 0], "kwargs":{}})], escape=escape)
        self.assertEqual(b, '[0,0,"*set*",["~",{"args":[["~@",650],"prop",0],"kwargs":{}},{"c":1}]]')
        c = j.encode(j.EnhancedBlock(dict(a={"z":[K(), ["~test", K()]], 5:11}), explicit=True), escape=escape)
        self.assertEqual(c, '["~",{"a":{"z":[["~@",650],["~~",["~test",["~@",650]]]],"5":11}},{"c":3}]')
        d = j.encode(dict(d=(100,200), h=j.EnhancedBlock(["~test",[5, ["~~",6]]]), ff=j.EnhancedBlock([U(20),"6ą7",{5:4, 0:23, 4:"kk/\t\bk"}], explicit=True)), escape=escape)
        self.assertEqual(d, '{"d":[100,200],"h":["~",["~~",["~test",[5,["~~",["~~",6]]]]],{"c":2}],"ff":["~",[["~u",20],"6ą7",{"5":4,"0":23,"4":"kk/\\t\\bk"}],{"c":1}]}')
        e = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[KK(), "prop", 0], "kwargs":{}})])
        self.assertEqual(e, '[0,0,"*set*",["~",{"args":[["~@",650,340],"prop",0],"kwargs":{}},{"c":1}]]')

    def test_no_api_object(self):
        "enhjson: Object (`print` function) with no API as an input -> encoded string with `~?` escape"

        a = j.encode(print)
        self.assertEqual(a, '["~",["~?","NoEnhJSONBlockError","(\'?\', \'UnknownObjectError\', \'<built-in function print>\')"],{"e":true}]')
        b = j.encode(print, escape=escape_lazy)
        self.assertEqual(b, '["~",["~?","NoEnhJSONBlockError","(b\'?\', \'NoEnhJSONAPIError\', \'<built-in function print>\')"],{"e":true}]')
        c = j.encode(j.EnhancedBlock(print))
        self.assertEqual(c, '["~",["~?","UnknownObjectError","<built-in function print>"],{"c":1}]')
        d = j.encode(j.EnhancedBlock(print), escape=escape_lazy)
        self.assertEqual(d, '["~",["~?","NoEnhJSONAPIError","<built-in function print>"],{"c":1}]')

    def test_simple_opt_policies(self):
        "enhjson: Inputs with different optimization policies -> Encoded strings"

        a = j.encode(j.EnhancedBlock([7, "a", [3,5,6]], opt=j.OptPolicy.always_count), escape=escape)
        self.assertEqual(a, '["~",[7,"a",[3,5,6]],{"c":0}]')
        b = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[K(), "prop", 0], "kwargs":{}}, opt=j.OptPolicy.none)], escape=escape)
        self.assertEqual(b, '[0,0,"*set*",["~",{"args":[["~@",650],"prop",0],"kwargs":{}},{}]]')
        c = j.encode(j.EnhancedBlock([7, "a", [3,5,6]], opt=j.OptPolicy.none), escape=escape)
        self.assertEqual(c, '[7,"a",[3,5,6]]')

    def test_escape(self):
        "enhjson: Bad escape routine -> Encoded strings"

        a = j.encode(j.EnhancedBlock([1,2,3,4,5]), escape=bad_escape)
        self.assertEqual(a, '["~",[1,2,["~?","IllformedEscTupleError","\\"it\'s not a tuple at all - it\'s a string\\""],4,5],{"c":1}]')
        b = j.encode([1,2,3,4,5], escape=bad_escape)
        self.assertEqual(b, '[1,2,["~",["~?","NoEnhJSONBlockError","(\'?\', \'IllformedEscTupleError\', \'\\"it\\\\\'s not a tuple at all - it\\\\\'s a string\\"\')"],{"e":true}],4,5]')
        c = j.encode(j.EnhancedBlock([1,2,1000,4,5]), escape=bad_escape)
        self.assertEqual(c, '["~",[1,2,["~?","IllformedEscTupleError","\'very long very long very long very long very long very long very long very long very long very long very long very long very lo"],4,5],{"c":1}]')


if __name__ == '__main__':
    unittest.main()