"""Parse BibTeX file into records."""

import bibtexparser
import warnings

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


def initialise(name, pad=""):
    """Return initial of author name."""
    if name:
        return pad + name[0] + "."
    else:
        return ""


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
    return date.year()


def format_authors(authors):
    """Format authors into a list."""
    output = []

    for auth in authors:
        name_parts = auth.split(",")
        name_parts = [n.strip() for n in reversed(name_parts)]

        name_parts = " ".join(name_parts)

        name = HumanName(name_parts)

        name_parts = (
            name.first + initialise(name.middle, " ") + " " + name.last
        )

        output.append(name_parts)

    return output


def format_keywords(keywords):
    """Format keywords by stripping away leading decimals.

    Returns
    -------
    List of tuples
        List of (category, keyword) pairs, with categories being spelled
        out according to the labelling scheme.
    """
    formatted_keywords = []
    for keyword in keywords.split(","):
        # We only split at the *first* occurrence of the keyword because
        # some keywords contain additional hyphens.
        tokens = keyword.split("-", 1)

        # This skips "bare" keywords; we handle those by assigning the
        # type of applicaion instead.
        if len(tokens) == 2:
            category = tokens[0].strip()
            keyword = tokens[1].strip()

            category_map = {
                "1": "applications",
                "2": "tools",
                "3": "data",
            }

            # Parent--child keyword; split it. We thus make the article
            # searchable using *both* tags. If an article is tagged
            # "images:3d", for example, we want it to appear when you
            # search for "images" and when you search for "images:3d".
            if ":" in keyword:
                parents = keyword.split(":")[:-1]

                # Add only the parent keyword; the full keyword will be
                # added afterwards anyway.
                for parent in parents:
                    formatted_keywords.append((category_map[category], parent))

            formatted_keywords.append((category_map[category], keyword))

        # Bare keyword, which indicates the "flavour" of a method, i.e.
        # whether the method contributes something new or confirms some
        # existing theory.
        elif len(tokens) == 1:
            flavour = tokens[0].strip()

            # Don't add empty tags.
            if flavour:
                formatted_keywords.append(("flavour", flavour))

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
    parser = BibTexParser(common_strings=True, customization=customisations)

    with open(filename) as f:
        db = bibtexparser.load(f, parser=parser)

    entries = [e for e in db.entries if "year" in e or "date" in e]
    entries = [process_entry(e) for e in entries]

    # Read file again without any customisations, thus making it
    # possible for us to include the "raw" entry.
    parser = BibTexParser(common_strings=True)

    with open(filename) as f:
        db = bibtexparser.load(f, parser=parser)

    raw_entries = [e for e in db.entries if "year" in e or "date" in e]
    entries = [dict(e, **{"raw": r}) for e, r in zip(entries, raw_entries)]

    return entries
