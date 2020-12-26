import mupf.plugins as plugins
import pkgutil
import importlib

_discovered_plugins = {}

def _collect_plugins():
    global _discovered_plugins
    _discovered_plugins = {
        name: importlib.import_module(name)
            for finder, name, ispkg in pkgutil.iter_modules(plugins.__path__, plugins.__name__ + ".")
    }

def iterate_with_predicate(predicate, public=True):
    _collect_plugins()
    for plugin_name, plugin_package in _discovered_plugins.items():
        plugin_name = plugin_name.removeprefix('mupf.plugins.')
        if plugin_name.startswith("_"):
            continue
        for var_name in dir(plugin_package):
            if public and var_name.startswith("_"):
                continue
            candidate = plugin_package.__dict__[var_name]
            if predicate(candidate):
                yield plugin_name, var_name, candidate

def iterate_by_supclass(class_):
    yield from iterate_with_predicate(lambda c: isinstance(c, type) and issubclass(c, class_))

def iterate_by_type(type_):
    yield from iterate_with_predicate(lambda c: type(c)==type_)

def inject(package_name, globs, iterator, **kwargs):
    for plugin_name, var_name, value in iterator(**kwargs):
        if var_name not in globs:
            globs[var_name] = value
            # TODO: propper logging
            # print(f'`{var_name}` injected into `{package_name}` from `{plugin_name}` plugin')
        else:
            pass
            # print(f'`{var_name}` NOT injected into `{package_name}` from `{plugin_name}` plugin due to collision')
