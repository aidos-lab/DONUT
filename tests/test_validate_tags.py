"""Tests for tag validation."""

from donut.validate_tags import (
    check_missing_categories,
    check_singleton_tags,
    check_near_duplicates,
    check_orphan_hierarchies,
)


def test_check_missing_categories(test_db):
    issues = check_missing_categories(test_db)
    # GUDHI software entry is skipped, but it has no apps/data tags
    # so only non-software entries are checked
    assert isinstance(issues, list)


def test_check_singleton_tags(test_db):
    singletons = check_singleton_tags(test_db)
    assert isinstance(singletons, list)
    singleton_tags = [tag for tag, _ in singletons]
    # "climate science" only appears in one paper
    assert "climate science" in singleton_tags


def test_check_near_duplicates(test_db):
    dupes = check_near_duplicates(test_db, threshold=0.85)
    assert isinstance(dupes, list)
    for item in dupes:
        assert len(item) == 3


def test_check_orphan_hierarchies(test_db):
    orphans = check_orphan_hierarchies(test_db)
    assert isinstance(orphans, list)
    orphan_tags = [tag for tag, _ in orphans]
    # "neuroscience:brain imaging" parent "neuroscience" exists
    assert "neuroscience:brain imaging" not in orphan_tags
