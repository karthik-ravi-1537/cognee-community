from collections.abc import Callable
from importlib import import_module
from typing import Any

from cognee.base_config import get_base_config

from .keywordsai_adapter import get_keywordsai_observe

get_observe_mod = import_module("cognee.modules.observability.get_observe")
_orig_get_observe: Callable[..., Any] = get_observe_mod.get_observe  # save


def _patched_get_observe():
    tool = get_base_config().monitoring_tool
    value = str(getattr(tool, "value", tool)).lower().replace("_", "")

    if value.startswith("observer."):
        value = value.split(".", 1)[1]

    if value == "keywordsai":
        return get_keywordsai_observe()
    return _orig_get_observe()


get_observe_mod.get_observe = _patched_get_observe  # type: ignore[attr-defined]
