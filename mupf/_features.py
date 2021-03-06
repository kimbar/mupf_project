import copy
from ._utils import removeprefix as __removeprefix

class __Feature:

    def __init__(self, internal_name, default):
        self.internal_name = internal_name
        self._default = default
        self._state = None

    def __repr__(self):
        return f"{('+' if self.state else '-')} mupf.F.{self.internal_name}"

    def __eq__(self, other):
        return self.internal_name == other.internal_name

    def __hash__(self):
        return hash(self.internal_name)

    def __neg__(self):
        if self._state is None:
            out = copy.copy(self)
            out._state = False
            return out
        self._state = not self._state
        return self

    def __pos__(self):
        if self._state is None:
            out = copy.copy(self)
            out._state = True
            return out
        return self

    @property
    def state(self):
        if self._state is None:
            return self._default
        return self._state


core_features = __Feature('core_features', True)
strict_feature_list = __Feature('strict_feature_list', False)
verbose_macros = __Feature('verbose_macros', False)
friendly_obj_names = __Feature('friendly_obj_names', False)
safe_dunders = __Feature('safe_dunders', True)
garbage_collection = __Feature('garbage_collection', True)

test_feature = __Feature('test_feature', True)
another_test_feat = __Feature('another_test_feat', False)

feature_list = [x for x in globals().values() if isinstance(x, __Feature)]

def __getattr__(name: str):
    global feature_list
    if name.startswith('_features__'):
        return globals()[__removeprefix(name, '_features')]
    if not name.startswith("_"):
        raise ValueError(f'User defined features names must begin with `_`, got `{name}`')
    feature = __Feature(name, True)
    if feature not in feature_list:
        feature_list.append(feature)
    return feature
