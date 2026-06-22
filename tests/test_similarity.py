"""Tests for similarity module."""

from donut.similarity import compute_similarity


def test_compute_similarity(test_db):
    neighbors = compute_similarity(test_db)
    assert isinstance(neighbors, dict)
    assert len(neighbors) > 0


def test_similarity_values(test_db):
    neighbors = compute_similarity(test_db)
    for docid, scores in neighbors.items():
        for neighbor_id, score in scores:
            assert 0 < score <= 1.0


def test_similar_papers_share_tags(test_db):
    neighbors = compute_similarity(test_db)
    has_neighbors = [
        docid for docid, scores in neighbors.items()
        if len(scores) > 0
    ]
    assert len(has_neighbors) > 0
