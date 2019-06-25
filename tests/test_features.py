"""Test suite for the `_enhjson.py` module
"""
import nose
from nose.tools import istest, nottest

from mupf import _features as F
import mupf

@istest
def name_consistency():
    """features: Module -> Variable names and internal names consistent
    """
    ok = []
    for var_name in dir(F):
        var = getattr(F, var_name)
        if isinstance(var, F.__Feature):
            ok.append(var_name == var.internal_name)
    assert all(ok)

@istest
def repr_consistency():
    """features: Module -> `__repr__` of features consistent with module name
    """
    feature = F.feature_list[0] 
    assert feature == eval(repr(feature), {'mupf': mupf})
