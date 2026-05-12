from __future__ import annotations

import sys
from importlib import import_module


_MODULE_ALIASES = {
    "analyzer": "refundradar.analyzer",
    "collector": "refundradar.collector",
    "exceptions": "refundradar.exceptions",
    "models": "refundradar.models",
    "nl_query": "refundradar.nl_query",
    "search_index": "refundradar.search_index",
    "storage": "refundradar.storage",
}

for _module_name, _target in _MODULE_ALIASES.items():
    sys.modules[f"{__name__}.{_module_name}"] = import_module(_target)


RadarStorage = import_module("refundradar.storage").RadarStorage


__all__ = ["RadarStorage"]
