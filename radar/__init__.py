from __future__ import annotations

import importlib
import sys


_ALIASES = {
    "analyzer": "refundradar.analyzer",
    "collector": "refundradar.collector",
    "exceptions": "refundradar.exceptions",
    "models": "refundradar.models",
    "nl_query": "refundradar.nl_query",
    "reporter": "refundradar.reporter",
    "search_index": "refundradar.search_index",
    "storage": "refundradar.storage",
}


for _name, _target in _ALIASES.items():
    sys.modules[f"{__name__}.{_name}"] = importlib.import_module(_target)


__all__ = sorted(_ALIASES)
