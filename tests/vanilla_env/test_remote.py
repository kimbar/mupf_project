"""Test suite for the `_remote.py` module
"""

import unittest

from mupf import _symbols as S
import mupf

class RemoteObj(unittest.TestCase):

    def setUp(self) -> None:
        print(self.shortDescription())

    def test_symbol_consistency(self):
        """features: Module -> Consistency of hardcoded symbols

        Some optimizations in `_remote.py` are made. Values of symbols are
        hardcoded and must be consistent with those defined in `_symbols.py`
        """

        self.assertEqual(S.client.internal_name, "_client")
        self.assertEqual(S.command.internal_name, "_command")
        self.assertEqual(S.json_esc_interface.internal_name, "_json_esc_interface")
        self.assertEqual(S.this.internal_name, "_this")
        self.assertEqual(S.rid.internal_name, "_rid")

        self.assertEqual(S.client.weakref, True)
        self.assertEqual(S.command.weakref, True)
        self.assertEqual(S.json_esc_interface.weakref, False)
        self.assertEqual(S.this.weakref, False)
        self.assertEqual(S.rid.weakref, False)


# import mupf
# from mupf._remote import RemoteObj

# class DummyClient():
#     def __init__(self):
#         self.command = set()    # `set` can be weak referenced
#         self._safe_dunders_feature = True

# def class_test():
#     client = DummyClient()
#     rem = RemoteObj(0, client)
#     assert isinstance(rem, RemoteObj)
#     assert not isinstance(rem, str)
