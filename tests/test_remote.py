"""Test suite for the `_enhjson.py` module
"""
import nose
from nose.tools import istest, nottest

import mupf
from mupf._remote import RemoteObj

class DummyClient():
    def __init__(self):
        self.command = set()    # `set` can be weak referenced
        self._safe_dunders_feature = True

@istest
def class_test():
    client = DummyClient()
    rem = RemoteObj(0, client)
    assert isinstance(rem, RemoteObj)
    assert not isinstance(rem, str)
