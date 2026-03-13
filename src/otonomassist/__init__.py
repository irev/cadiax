"""Compatibility shim for the legacy `otonomassist` package name."""

from __future__ import annotations

import importlib
import importlib.abc
import importlib.util
import sys
from types import ModuleType

import cadiax as _cadiax
from cadiax import *  # noqa: F403
from cadiax import __all__ as _cadiax_all
from cadiax import __author__, __version__


class _CadiaxAliasLoader(importlib.abc.Loader):
    """Load `otonomassist.*` modules by aliasing them to `cadiax.*`."""

    def __init__(self, fullname: str) -> None:
        self.fullname = fullname
        self.mapped_name = fullname.replace("otonomassist", "cadiax", 1)

    def create_module(self, spec):  # noqa: ANN001
        module = importlib.import_module(self.mapped_name)
        sys.modules[self.fullname] = module
        return module

    def exec_module(self, module: ModuleType) -> None:
        sys.modules[self.fullname] = module


class _CadiaxAliasFinder(importlib.abc.MetaPathFinder):
    """Resolve legacy `otonomassist.*` imports to `cadiax.*` modules."""

    def find_spec(self, fullname: str, path=None, target=None):  # noqa: ANN001
        if not fullname.startswith("otonomassist."):
            return None

        mapped_name = fullname.replace("otonomassist", "cadiax", 1)
        mapped_spec = importlib.util.find_spec(mapped_name)
        if mapped_spec is None:
            return None

        is_package = mapped_spec.submodule_search_locations is not None
        spec = importlib.util.spec_from_loader(
            fullname,
            _CadiaxAliasLoader(fullname),
            origin=mapped_spec.origin,
            is_package=is_package,
        )
        if spec and is_package:
            spec.submodule_search_locations = list(mapped_spec.submodule_search_locations or [])
        return spec


if not any(isinstance(finder, _CadiaxAliasFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _CadiaxAliasFinder())

__all__ = list(_cadiax_all)
__path__ = _cadiax.__path__
if __spec__ is not None:
    __spec__.submodule_search_locations = list(_cadiax.__path__)
