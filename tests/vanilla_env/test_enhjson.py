"""Test suite for the `_enhjson.py` module
"""
import unittest
from mupf import _enhjson as j


class U:
    def __init__(self, x):
        self.x = x
    def json_esc(self):
        return "u", self.x

class K:
    def json_esc(self):
        return "@", 650

class KK:
    def json_esc(self):
        return "@", 650, 340


class EnhJSON(unittest.TestCase):

    def setUp(self):
        print(self.shortDescription())

    def test_basic(self):
        "enhjson: Simple input -> Encoded string"

        a = j.encode("basic")
        self.assertEqual(a, '"basic"')

    def test_complex(self):
        "enhjson: Complex inputs -> Encoded strings"

        a = j.encode(j.EnhancedBlock([7, "a", j.EnhancedBlock([3,5,6])]) )
        self.assertEqual(a, '[7,"a",[3,5,6]]')
        b = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[K(), "prop", 0], "kwargs":{}})] )
        self.assertEqual(b, '[0,0,"*set*",["~",{"args":[["~@",650],"prop",0],"kwargs":{}},{"c":1}]]')
        c = j.encode(j.EnhancedBlock(dict(a={"z":[K(), ["~test", K()]], 5:11}), explicit=True))
        self.assertEqual(c, '["~",{"a":{"z":[["~@",650],["~~",["~test",["~@",650]]]],"5":11}},{"c":3}]')
        d = j.encode(dict(d=(100,200), h=j.EnhancedBlock(["~test",[5, ["~~",6]]]), ff=j.EnhancedBlock([U(20),"6ą7",{5:4, 0:23, 4:"kk/\t\bk"}], explicit=True)))
        self.assertEqual(d, '{"d":[100,200],"h":["~",["~~",["~test",[5,["~~",["~~",6]]]]],{"c":2}],"ff":["~",[["~u",20],"6ą7",{"5":4,"0":23,"4":"kk/\\t\\bk"}],{"c":1}]}')
        e = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[KK(), "prop", 0], "kwargs":{}})] )
        self.assertEqual(e, '[0,0,"*set*",["~",{"args":[["~@",650,340],"prop",0],"kwargs":{}},{"c":1}]]')

    def test_no_api_object(self):
        "enhjson: Object (`print` function) with no API as an input -> encoded string with `~?` escape"

        a = j.encode(j.EnhancedBlock(print))
        self.assertEqual(a, '["~",["~?","NoEnhJSONAPIError","<built-in function print>"],{"c":1}]')

    def test_simple_opt_policies(self):
        "enhjson: Inputs with different optimization policies -> Encoded strings"

        a = j.encode(j.EnhancedBlock([7, "a", [3,5,6]], opt=j.OptPolicy.always_count) )
        self.assertEqual(a, '["~",[7,"a",[3,5,6]],{"c":0}]')
        b = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[K(), "prop", 0], "kwargs":{}}, opt=j.OptPolicy.none)])
        self.assertEqual(b, '[0,0,"*set*",["~",{"args":[["~@",650],"prop",0],"kwargs":{}},{}]]')
        c = j.encode(j.EnhancedBlock([7, "a", [3,5,6]], opt=j.OptPolicy.none) )
        self.assertEqual(c, '[7,"a",[3,5,6]]')


if __name__ == '__main__':
    unittest.main()