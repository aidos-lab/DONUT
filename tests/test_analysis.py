"""Tests for analysis module."""

from donut.analysis import compute_statistics, compute_tag_cooccurrence


def test_compute_statistics(test_db):
    stats = compute_statistics(test_db)
    assert "years" in stats
    assert "top_tags" in stats
    assert "top_authors" in stats
    assert "total_papers" in stats
    assert "total_software" in stats


def test_statistics_counts(test_db):
    stats = compute_statistics(test_db)
    assert stats["total_papers"] == 3
    assert stats["total_software"] == 1


def test_statistics_years(test_db):
    stats = compute_statistics(test_db)
    assert stats["years"]["2024"] == 2
    assert stats["years"]["2023"] == 1
    assert stats["years"]["2022"] == 1


def test_compute_tag_cooccurrence(test_db):
    edges = compute_tag_cooccurrence(test_db, min_weight=1)
    assert isinstance(edges, list)
    assert len(edges) > 0


def test_cooccurrence_edge_structure(test_db):
    edges = compute_tag_cooccurrence(test_db, min_weight=1)
    for edge in edges:
        assert "source" in edge
        assert "target" in edge
        assert "weight" in edge
        assert edge["weight"] >= 1


def test_cooccurrence_known_pair(test_db):
    edges = compute_tag_cooccurrence(test_db, min_weight=1)
    pairs = {
        (e["source"], e["target"]) for e in edges
    }
    assert (
        ("persistent homology", "point cloud") in pairs
        or ("point cloud", "persistent homology") in pairs
    )
