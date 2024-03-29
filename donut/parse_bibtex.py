"""Parse BibTeX file into records."""

import bibtexparser

import dateutil.parser

from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import author
from bibtexparser.customization import convert_to_unicode

from nameparser import HumanName

from titlecase import titlecase


def customisations(record):
    """Customise record parsing.

    This function is run prior to parsing a full BibTeX record. It
    ensures that the record is formatted correctly.
    """
    record = convert_to_unicode(record)
    record = author(record)
    return record


def fix_raw_latex(field):
    """Fix raw LaTeX commands."""
    raw = [
        "\\emph",
        "\\mbox",
        "\\textbf",
        # This is probably due to a bug in the parser; ideally, raw
        # markup should be replaced 'as-is.'
        "\\Texttt",
    ]

    for kw in raw:
        field = field.replace(kw, "")

    # Replace quotes and let our Markdown system do the right thing
    # here.
    field = field.replace("`", "'")

    # Non-breaking space handling
    field = field.replace("~", "&nbsp;")

    return field


def format_title(entry):
    """Create formatted title from entry."""
    raw_title = entry["title"]
    raw_title = titlecase(raw_title)
    raw_title = fix_raw_latex(raw_title)

    return raw_title


def format_year(entry):
    """Get year information from entry or try to parse it."""
    if "year" in entry:
        return entry.get("year")

    date = dateutil.parser.parse(entry.get("date", ""))

    # Note that we actually want to return a string here since no fields
    # are encoded in other data types.
    return str(date.year)


def format_authors(authors):
    """Format authors into a list."""
    output = []

    for auth in authors:
        name_parts = auth.split(",")
        name_parts = [n.strip() for n in reversed(name_parts)]

        name_parts = " ".join(name_parts)

        name = HumanName(name_parts)
        name_parts = name.first + " " + name.middle + " " + name.last

        output.append(name_parts)

    return output


def format_metadata(keywords, identifier):
    """Extract optional metadata from keywords.

    Metadata are keywords that start with an alphabetic character. This
    function provides a generic entry point for extracting all types of
    metadata. The client has to set up the call correctly.

    Parameters
    ----------
    keywords : str
        Keyword string, as formatted by the backend. Keywords are
        separated by commas.

    identifier : str
        Indicates the identifier to extract, such as "V" for videos. All
        other metadata will be ignored.

    Returns
    -------
    List of tuples
        List of (url, title) pairs. The title is optional and will be
        empty if the entry does not define it.
    """
    metadata = []
    for keyword in keywords.split(","):
        # We only split at the *first* occurrence of the keyword because
        # some keywords contain additional hyphens.
        tokens = keyword.split("-", 1)

        # This skips "bare" keywords; we handle those by assigning the
        # type of application instead.
        if len(tokens) == 2:
            category = tokens[0].strip()
            keyword = tokens[1].strip()

            if category != identifier:
                continue

            tokens = keyword.split()

            if len(tokens) == 0:
                continue

            url = tokens[0]
            title = ""

            if len(tokens) >= 2:
                title = tokens[1]

            metadata.append((url, title))

    return metadata


def format_keywords(keywords):
    """Format keywords by stripping away leading decimals.

    A keyword has to start with a number, indicating the category,
    followed by a string.

    Returns
    -------
    Set of tuples
        Set of (category, keyword) pairs, with categories being spelled
        out according to the labelling scheme.
    """
    formatted_keywords = set()
    for keyword in keywords.split(","):
        # We only split at the *first* occurrence of the keyword because
        # some keywords contain additional hyphens.
        tokens = keyword.split("-", 1)

        # This skips "bare" keywords; we handle those by assigning the
        # type of application instead.
        if len(tokens) == 2:
            category = tokens[0].strip()
            keyword = tokens[1].strip()

            category_map = {
                "1": "applications",
                "2": "tools",
                "3": "data",
            }

            # If we get an alphabetic character, this is metadata and
            # needs to be handled elsewhere.
            if category.isalpha():
                continue

            # Parent--child keyword; split it. We thus make the article
            # searchable using *both* tags. If an article is tagged
            # "images:3d", for example, we want it to appear when you
            # search for "images" and when you search for "images:3d".
            if ":" in keyword:
                parts = keyword.split(":")

                # Add subcategory for *nested* categories, including
                # those that have more than one parent. For example,
                # this splits "foo:bar:baz" into "foo:bar" and "foo"
                # respectively.
                for index in range(len(parts) - 1):
                    subcategory = ":".join(parts[: -(index + 1)])
                    formatted_keywords.add(
                        (category_map[category], subcategory)
                    )

            # Add the original keyword again, i.e. "foo:bar:baz" without
            # additional formatting. This ensures an intact hierarchy.
            formatted_keywords.add((category_map[category], keyword))

        # Bare keyword, which indicates the "flavour" of a method, i.e.
        # whether the method contributes something new or confirms some
        # existing theory.
        elif len(tokens) == 1:
            flavour = tokens[0].strip()

            # Not every "bare" flavour should be shown.
            valid_flavours = ["confirm", "innovate"]

            # Don't add empty tags or invalid flavours.
            if flavour and flavour.lower() in valid_flavours:
                formatted_keywords.add(("flavour", flavour))

    # The `set` ensures that we only add keywords at most once even if
    # they occur multiple times (this can happen in case hierarchical
    # tags are being used).
    return sorted(set(formatted_keywords))


def format_doi(doi):
    """Format DOI and strip away URL parts."""
    doi = doi.replace("https://dx.doi.org/", "")
    doi = doi.replace("https://doi.org/", "")
    return doi


def process_entry(entry):
    """Process a single bibliographic entry."""
    # Will store the resulting entry as a nice dictionary, containing
    # relevant information about the paper.
    output = {
        "title": format_title(entry),
        "author": format_authors(entry["author"]),
        "keywords": format_keywords(entry.get("keywords", "")),
        "code": format_metadata(entry.get("keywords", ""), "C"),
        "data": format_metadata(entry.get("keywords", ""), "D"),
        "videos": format_metadata(entry.get("keywords", ""), "V"),
        "abstract": entry.get("abstract", ""),
        "year": format_year(entry),
        "doi": format_doi(entry.get("doi", "")),
        "url": entry.get("url", ""),
        "id": entry["ID"],
        "type": entry["ENTRYTYPE"],
    }

    return output


def get_entries(filename):
    """Get entries from file."""
    parser = BibTexParser(
        common_strings=True,
        customization=customisations,
        ignore_nonstandard_types=False,
    )

    with open(filename) as f:
        db = bibtexparser.load(f, parser=parser)

    def _get_valid_entries(db):
        return [e for e in db.entries if "year" in e or "date" in e]

    entries = _get_valid_entries(db)
    entries = [process_entry(e) for e in entries]

    # Read file again without any customisations, thus making it
    # possible for us to include the "raw" entry.
    parser = BibTexParser(common_strings=True, ignore_nonstandard_types=False)

    with open(filename) as f:
        db = bibtexparser.load(f, parser=parser)

    raw_entries = _get_valid_entries(db)
    entries = [dict(e, **{"raw": r}) for e, r in zip(entries, raw_entries)]

    return entries
