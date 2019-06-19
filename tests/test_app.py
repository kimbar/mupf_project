"""Test suite for the `_app.py` module
"""

import nose
from nose.tools import istest, nottest
from nose.tools import assert_raises

import mupf

@istest
def not_a_feature_type():
    with assert_raises(TypeError) as cm:
        app = mupf.App(
            features = (30, 50)
        )
    assert str(cm.exception) == 'all features must be of `mupf.F.__Feature` type'

    with assert_raises(TypeError) as cm:
        app = mupf.App(
            features = + mupf.F.core_features
        )
    assert str(cm.exception) == '`feature` argumnet of `App` must be a **container** of features'

    

