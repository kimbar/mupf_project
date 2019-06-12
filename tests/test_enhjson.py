"""Test suite for the `_enhjson.py` module
"""
import nose
from nose.tools import istest, nottest

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


@istest
def basic():
    """enhjson: Encode superbasic input
    """
    a = j.encode("basic")
    assert a == '"basic"'

@istest
def complex():
    """enhjson: Encode some complex input
    """
    #
    a = j.encode(j.EnhancedBlock([7, "a", j.EnhancedBlock([3,5,6])]) )
    assert a == '[7,"a",[3,5,6]]'
    #
    b = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[K(), "prop", 0], "kwargs":{}})] )
    assert b == '[0,0,"*set*",["~",{"args":[["~@",650],"prop",0],"kwargs":{}},{"c":1}]]'
    #
    c = j.encode(j.EnhancedBlock(dict(a={"z":[K(), ["~test", K()]], 5:11}), explicit=True))
    assert c == '["~",{"a":{"z":[["~@",650],["~~",["~test",["~@",650]]]],"5":11}},{"c":3}]'
    #
    d = j.encode(dict(d=(100,200), h=j.EnhancedBlock(["~test",[5, ["~~",6]]]), ff=j.EnhancedBlock([U(20),"6ą7",{5:4, 0:23, 4:"kk/\t\bk"}], explicit=True)))
    assert d == '{"d":[100,200],"h":["~",["~~",["~test",[5,["~~",["~~",6]]]]],{"c":2}],"ff":["~",[["~u",20],"6ą7",{"5":4,"0":23,"4":"kk/\\t\\bk"}],{"c":1}]}'
    #
    e = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[KK(), "prop", 0], "kwargs":{}})] )
    assert e == '[0,0,"*set*",["~",{"args":[["~@",650,340],"prop",0],"kwargs":{}},{"c":1}]]'

@istest
def no_api_object():
    """enhjson: Encode object (`print` function) with no API
    """
    a = j.encode(j.EnhancedBlock(print)) 
    assert a == '["~",["~?","NoEnhJSONAPIError","<built-in function print>"],{"c":1}]'

@istest
def simple_opt_policies():
    """enhjson: Encode some input with different optimization policies
    """
    a = j.encode(j.EnhancedBlock([7, "a", [3,5,6]], opt=j.OptPolicy.always_count) )
    assert a == '["~",[7,"a",[3,5,6]],{"c":0}]'
    #
    b = j.encode([0,0,'*set*',j.EnhancedBlock({"args":[K(), "prop", 0], "kwargs":{}}, opt=j.OptPolicy.none)])
    assert b == '[0,0,"*set*",["~",{"args":[["~@",650],"prop",0],"kwargs":{}},{}]]'
    #
    c = j.encode(j.EnhancedBlock([7, "a", [3,5,6]], opt=j.OptPolicy.none) )
    assert c == '[7,"a",[3,5,6]]'
