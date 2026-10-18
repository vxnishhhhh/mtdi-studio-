"""Shared namespace plumbing for the split application modules.

The instrument began life as one 13,000 line script whose sections referenced each
other freely. The sections now live in separate modules in a fixed order. Each module
starts by inheriting the names of the modules before it, and ``unify`` gives every
module the final union once all of them are loaded. That reproduces the single file
semantics exactly while keeping each concern in its own file.
"""
import importlib

ORDER = ["common", "sensors", "intelligence", "system", "tokens", "theme", "browser",
         "webapp", "reports", "charts", "pages", "routing"]
_SKIP = {"__name__", "__file__", "__doc__", "__package__", "__loader__", "__spec__",
         "__builtins__", "__cached__", "__path__"}


def inherit(namespace, *module_names):
    """Copy every public and private name from the named sibling modules."""
    for name in module_names:
        module = importlib.import_module("studio." + name)
        for key, value in vars(module).items():
            if key not in _SKIP:
                namespace[key] = value


def modules():
    return [importlib.import_module("studio." + name) for name in ORDER]


def unify():
    """Give every module the final binding of every name, later modules winning."""
    union = {}
    loaded = modules()
    for module in loaded:
        for key, value in vars(module).items():
            if key not in _SKIP:
                union[key] = value
    for module in loaded:
        vars(module).update(union)
    return union


class SharedNamespace(dict):
    """A dict view of the unified namespace whose writes reach every module."""

    def __init__(self):
        super().__init__(unify())
        self._modules = modules()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        for module in self._modules:
            setattr(module, key, value)
