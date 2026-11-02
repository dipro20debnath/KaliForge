"""Catalog loader: merges the static segment data, validates records and
exposes search/index helpers. Custom (user-imported) tools are merged on top.
"""
from __future__ import annotations

import copy
from typing import Iterable

from core.categories import CATEGORY_BY_ID
from tools.catalog_data_a import SEGMENTS_A
from tools.catalog_data_b import SEGMENTS_B

_REQUIRED = {"id", "name", "category", "desc", "binary"}
VALID_RISK = {"info", "caution", "dangerous"}


def _normalise(tool: dict) -> dict:
    tool = copy.deepcopy(tool)
    missing = _REQUIRED - set(tool)
    if missing:
        raise ValueError(f"tool {tool.get('id', '?')} missing fields: {sorted(missing)}")
    if tool["category"] not in CATEGORY_BY_ID:
        raise ValueError(f"tool {tool['id']} has unknown category {tool['category']}")
    tool.setdefault("package", "")
    tool.setdefault("homepage", "")
    tool.setdefault("docs", "")
    tool.setdefault("lab_only", False)
    tool.setdefault("tags", [])
    tool.setdefault("commands", [])
    tool.setdefault("custom", False)
    risk = tool.get("risk", "info")
    tool["risk"] = risk if risk in VALID_RISK else "info"
    return tool


class Catalog:
    """Immutable-ish view over the built-in catalog plus merged custom tools."""

    def __init__(self, extra: Iterable[dict] | None = None):
        self._tools: dict[str, dict] = {}
        for record in list(SEGMENTS_A) + list(SEGMENTS_B):
            norm = _normalise(record)
            self._tools[norm["id"]] = norm
        if extra:
            self.merge(extra)

    def merge(self, extra: Iterable[dict]) -> None:
        for record in extra:
            try:
                norm = _normalise(record)
            except ValueError:
                continue
            norm["custom"] = True
            self._tools[norm["id"]] = norm

    # ---------------------------------------------------------------- access
    def all(self) -> list[dict]:
        return [copy.deepcopy(t) for t in self._tools.values()]

    def get(self, tool_id: str) -> dict | None:
        tool = self._tools.get(tool_id)
        return copy.deepcopy(tool) if tool else None

    def by_category(self, category: str) -> list[dict]:
        return [copy.deepcopy(t) for t in self._tools.values() if t["category"] == category]

    def categories_present(self) -> set[str]:
        return {t["category"] for t in self._tools.values()}

    def count(self) -> int:
        return len(self._tools)

    def search(self, query: str) -> list[dict]:
        query = (query or "").strip().lower()
        if not query:
            return self.all()
        results = []
        for tool in self._tools.values():
            haystack = " ".join([
                tool["id"], tool["name"], tool["desc"], tool["category"],
                " ".join(tool.get("tags", [])),
            ]).lower()
            if query in haystack:
                results.append(copy.deepcopy(tool))
        return results


# default shared instance for simple callers / tests
DEFAULT_CATALOG = Catalog()
