"""Test suite for the `_enhjson.py` module
"""
import nose
from nose.tools import istest, nottest

from mupf import _features as F


@istest
def name_consistency():
    """features: variable names and internal names consistent
    """
    ok = []
    for var_name in dir(F):
        var = getattr(F, var_name)
        if isinstance(var, F.__Feature):
            ok.append(var_name == var.internal_name)
    assert all(ok)
    