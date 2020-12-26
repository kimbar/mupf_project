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

def iterate_by_class(class_):
    _collect_plugins()
    for plugin_name, plugin_package in _discovered_plugins.items():
        if not plugin_name.lstrip('mupf.plugins.').startswith("_"):
            for var_name in dir(plugin_package):
                candidate = plugin_package.__dict__[var_name]
                if isinstance(candidate, type) and issubclass(candidate, class_):
                    yield var_name, candidate

def inject_by_class(globs, class_):
    for class_name, class_ in iterate_by_class(class_):
        globs[class_name] = class_
