"""Parse BibTeX file into records."""

import bibtexparser
import json

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


def initialise(name, pad=''):
    """Return initial of author name."""
    if name:
        return pad + name[0] + '.'
    else:
        return ''


def format_title(entry):
    """Create formatted title from entry."""
    raw_title = entry['title']
    raw_title = titlecase(raw_title)
    raw_title = fix_raw_latex(raw_title)

    return raw_title


def format_authors(authors):
    """Format authors into a list."""
    output = []

    for auth in authors:
        name_parts = auth.split(',')
        name_parts = [n.strip() for n in reversed(name_parts)]

        name_parts = ' '.join(name_parts)

        name = HumanName(name_parts)

        name_parts = initialise(name.first)             \
            + initialise(name.middle, '&thinsp;')       \
            + ' '                                       \
            + name.last

        output.append(name_parts)

    return output


def make_eprint_url(paper):
    """Return URL from paper with `eprint`."""
    url = None
    eprint = paper['eprint']
    if paper['archiveprefix'] == 'arXiv':
        url = f'https://arxiv.org/abs/{eprint}'

    return url


def get_pubstate(paper):
    """Return publication state of paper."""
    state = paper['pubstate']
    if state == 'inpress':
        return 'in press'
    elif state == 'inpreparation':
        return 'in preparation'
    else:
        return state


def fix_raw_latex(field):
    """Fix raw LaTeX commands."""
    raw = [
        '\\emph',
        '\\mbox',
        '\\textbf',
        # This is probably due to a bug in the parser; ideally, raw
        # markup should be replaced 'as-is.'
        '\\Texttt',
    ]

    for kw in raw:
        field = field.replace(kw, '')

    # Replace quotes and let our Markdown system do the right thing
    # here.
    field = field.replace('`', '\'')

    # Non-breaking space handling
    field = field.replace('~', '&nbsp;')

    return field


def process_entry(entry):
    """Process a single bibliographic entry."""
    # Will store the resulting entry as a nice dictionary, containing
    # relevant information about the paper.
    output = {
        'title': format_title(entry),
        'author': format_authors(entry['author']),
        'id': entry['ID'],
        'type': entry['ENTRYTYPE']
    }

    return output


########################################################################
# HIC SVNT DRACONES
########################################################################

parser = BibTexParser(
    common_strings=True,
    customization=customisations
)

with open('/tmp/tda.bib') as f:
    db = bibtexparser.load(f, parser=parser)

entries = [e for e in db.entries if 'year' in e]
entries = [process_entry(e) for e in entries]
