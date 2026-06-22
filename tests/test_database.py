"""Tests for database module."""

from donut.database import search, get_documents, compute_facets


def test_search_returns_results(test_db):
    results = search(test_db, "homology")
    assert results is not None
    matches, corrected = results
    assert len(matches) >= 1


def test_search_sort_by_year_desc(test_db):
    results = search(test_db, "persistent homology", sort_by="year",
                     reverse=True)
    matches, _ = results
    years = [m["document"]["year"] for m in matches]
    assert years == sorted(years, reverse=True)


def test_search_sort_by_year_asc(test_db):
    results = search(test_db, "persistent homology", sort_by="year",
                     reverse=False)
    matches, _ = results
    years = [m["document"]["year"] for m in matches]
    assert years == sorted(years)


def test_search_empty_returns_none(test_db):
    assert search(test_db, None) is None
    assert search(test_db, "") is None


def test_search_with_pagination(test_db):
    all_results = search(test_db, "persistent homology")
    all_matches, _ = all_results
    total = len(all_matches)
    assert total >= 2

    page1 = search(test_db, "persistent homology", offset=0, limit=1)
    matches1, _ = page1
    assert len(matches1) == 1

    page2 = search(test_db, "persistent homology", offset=1, limit=1)
    matches2, _ = page2
    assert len(matches2) >= 1
    assert matches1[0]["id"] != matches2[0]["id"]


def test_get_documents_all(test_db):
    all_docs = get_documents(test_db)
    assert len(all_docs) == 4


def test_get_documents_with_pagination(test_db):
    page1 = get_documents(test_db, offset=0, limit=2)
    assert len(page1) == 2

    page2 = get_documents(test_db, offset=2, limit=2)
    assert len(page2) == 2

    ids_page1 = {d["id"] for d in page1}
    ids_page2 = {d["id"] for d in page2}
    assert ids_page1.isdisjoint(ids_page2)


def test_get_documents_with_entry_type_filter(test_db):
    papers = get_documents(test_db, entry_type="article")
    assert all(
        d["document"]["raw"]["ENTRYTYPE"] == "article"
        for d in papers
    )
    assert len(papers) == 3

    software = get_documents(test_db, entry_type="software")
    assert all(
        d["document"]["raw"]["ENTRYTYPE"] == "software"
        for d in software
    )
    assert len(software) == 1


def test_compute_facets(test_db):
    all_docs = get_documents(test_db)
    facets = compute_facets(all_docs)
    assert "tags" in facets
    assert "years" in facets
    assert "types" in facets


def test_facets_tag_counts(test_db):
    all_docs = get_documents(test_db)
    facets = compute_facets(all_docs)
    # 3 papers + 1 software entry have "persistent homology"
    assert facets["tags"]["tools"]["persistent homology"] == 4


def test_facets_year_counts(test_db):
    all_docs = get_documents(test_db)
    facets = compute_facets(all_docs)
    assert facets["years"]["2024"] == 2
