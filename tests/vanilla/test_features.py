"""Test suite for the `_features.py` module
"""
import unittest

from mupf import _features as F
import mupf

class Features(unittest.TestCase):

    def setUp(self) -> None:
        print(self.shortDescription())

    def test_name_consistency(self):
        "features: Module -> Variable names and internal names consistent"

        ok = []
        for var_name in dir(F):
            var = getattr(F, var_name)
            if isinstance(var, F.__dict__['__Feature']):
                ok.append(var_name == var.internal_name)
        self.assertTrue(all(ok))

    def test_repr_consistency(self):
        "features: Module -> `__repr__` of features consistent with module name"

        feature = F.feature_list[0]
        self.assertEqual(feature, eval(repr(feature), {'mupf': mupf}))
