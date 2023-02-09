"""General utilities module.

The purpose of this module is to provide utility functions that take
care of the heavy lifting, as opposed to letting `jinja2` handle it.
"""


def flat_tags_to_hierarchy(tags):
    """Turn flat tags into a hierarchy.

    This function takes a dictionary of categories and corresponding
    tags and turns it into a hierarchy. To this end, tag names that
    contain nested information will be prefixed by special instructions
    to the `jinja2` parser for increasing or decreasing the hierarchy
    level.

    As an example, a list of tags (foo, foo:bar, foo:bar:baz) of some
    category (emitted for simplicity) will be turned into a list with
    additional information to indicate the levels: (foo, L+, foo:bar,
    L+, foo:bar:baz, L-, L-).

    Parameters
    ----------
    tags: dict
        Dictionary containing categories as keys, and a list of
        tags/keywords as the respective values.

    Returns
    -------
    dict
        Dictionary with the same categories but with information about
        the levels attached.
    """
    hierarchical_tags = {}
    for category, keywords in tags.items():
        level = 0

        hierarchical_keywords = []

        for keyword, count in keywords:
            keyword_level = keyword.count(":")

            # Check how many hierarchies we have to emit. This is meant
            # to be symmetrical but in reality, the increasing tags can
            # only ever increase by one since we automatically generate
            # all the intermittent hierarchies. Hence, there is no need
            # to handle this case.
            if keyword_level > level:
                hierarchical_keywords.append(("L+", 0))

            # After a deep hierarchy, we may have to decrease the level
            # somewhat.
            elif keyword_level < level:
                for i in range(level - keyword_level):
                    hierarchical_keywords.append(("L-", 0))

            level = keyword_level
            hierarchical_keywords.append((keyword, count))

        # Check whether we have to decrease the level further in case
        # the last tag is a hierarchical one.
        for i in range(level):
            hierarchical_keywords.append(("L-", 0))

        hierarchical_tags[category] = hierarchical_keywords

    return hierarchical_tags
