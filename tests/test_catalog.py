from core.categories import CATEGORIES
from tools.catalog import Catalog, DEFAULT_CATALOG


def test_catalog_has_100_plus_tools():
    assert DEFAULT_CATALOG.count() >= 100


def test_every_category_populated():
    present = DEFAULT_CATALOG.categories_present()
    assert present == {c["id"] for c in CATEGORIES}
    for cat in CATEGORIES:
        assert DEFAULT_CATALOG.by_category(cat["id"]), f"empty category {cat['id']}"


def test_unique_ids_and_required_fields():
    ids = [t["id"] for t in DEFAULT_CATALOG.all()]
    assert len(ids) == len(set(ids))
    for tool in DEFAULT_CATALOG.all():
        for field in ("id", "name", "category", "desc", "binary", "risk"):
            assert tool[field] != "" or field == "desc"
        assert tool["risk"] in {"info", "caution", "dangerous"}


def test_search_matches_name_and_tags():
    assert any(t["id"] == "nmap" for t in DEFAULT_CATALOG.search("nmap"))
    assert any(t["id"] == "hashcat" for t in DEFAULT_CATALOG.search("gpu"))
    assert DEFAULT_CATALOG.search("zzz-nope") == []


def test_merge_custom_tool():
    cat = Catalog(extra=[{
        "id": "x-tool", "name": "X", "category": "recon", "desc": "d",
        "binary": "xt", "risk": "info",
    }])
    assert cat.get("x-tool")["custom"] is True
    assert cat.count() == DEFAULT_CATALOG.count() + 1


def test_lab_only_tools_are_flagged():
    sqlmap = DEFAULT_CATALOG.get("sqlmap")
    assert sqlmap["lab_only"] is True
    assert sqlmap["risk"] == "dangerous"
