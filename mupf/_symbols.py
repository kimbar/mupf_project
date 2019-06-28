class _Symbol:
    def __init__(self, internal_name, readonly=False):
        self.internal_name = internal_name
        self.readonly = readonly

    def __eq__(self, other):
        return self.internal_name == other.internal_name

    def __hash__(self):
        return hash(self.internal_name)

    def __repr__(self):
        return "[Symbol: {}]".format(self.internal_name.lstrip('_'))


this = _Symbol("_this", readonly=True)
rid = _Symbol("_rid", readonly=True)
client = _Symbol("_client", readonly=True)
json_esc_interface = _Symbol("_json_esc_interface", readonly=True)
dunder_class = _Symbol("")

def __getattr__(name: str) -> _Symbol:
    return _Symbol('_'+name)
