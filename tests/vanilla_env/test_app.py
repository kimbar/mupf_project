"""Test suite for the `_app.py` module
"""
import unittest
import mupf


class App_Features(unittest.TestCase):
    """app: `App` given illegal object as feature list -> Fail with `TypeError` exception
    """

    def setUp(self) -> None:
        print(self.shortDescription())

    def test_feature_types(self):
        "app: `App` given illegal object as feature list (ints) -> Fail with `TypeError` exception"
        with self.assertRaises(TypeError) as cm:
            app = mupf.App(
                features = (30, 50)
            )
        print('Exception text:', cm.exception)
        self.assertEqual(str(cm.exception), 'all features must be of `mupf.F.__Feature` type')

    def test_feature_container_type(self):
        "app: `App` given illegal object as feature list (not iterable) -> Fail with `TypeError` exception"
        with self.assertRaises(TypeError) as cm:
            app = mupf.App(
                features = + mupf.F.core_features
            )
        print('Exception text:', cm.exception)
        self.assertEqual(str(cm.exception), '`feature` argumnet of `App` must be a **container** of features')


if __name__ == '__main__':
    unittest.main()