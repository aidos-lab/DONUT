"""Parse BibTeX file into records."""

import bibtexparser

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


def format_authors(authors):
    """Format authors into a list."""
    output = []

    for auth in authors:
        name_parts = auth.split(",")
        name_parts = [n.strip() for n in reversed(name_parts)]

        name_parts = " ".join(name_parts)

        name = HumanName(name_parts)

        name_parts = (
            name.first
            + initialise(name.middle, " ")
            + " "
            + name.last
        )

        output.append(name_parts)

    return output


def process_entry(entry):
    """Process a single bibliographic entry."""
    # Will store the resulting entry as a nice dictionary, containing
    # relevant information about the paper.
    output = {
        "title": format_title(entry),
        "author": format_authors(entry["author"]),
        "id": entry["ID"],
        "type": entry["ENTRYTYPE"],
    }

    return output


def get_entries(filename):
    """Get entries from file."""
    parser = BibTexParser(common_strings=True, customization=customisations)

    with open(filename) as f:
        db = bibtexparser.load(f, parser=parser)

    entries = [e for e in db.entries if "year" in e]
    entries = [process_entry(e) for e in entries]

    return entries
