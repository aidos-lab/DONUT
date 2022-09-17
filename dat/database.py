"""Database module."""

import json
import xapian

from dat.parse_bibtex import get_entries


def index_documents(data_filename, database_dir):
    """Index documents from data file.

    Parameters
    ----------
    data_filename : str
        Filename for loading data from

    database_dir : str
        Directory for database
    """
    db = xapian.WritableDatabase(database_dir, xapian.DB_CREATE_OR_OPEN)

    termgenerator = xapian.TermGenerator()
    termgenerator.set_stemmer(xapian.Stem("en"))

    # TODO: Make this configurable; we could potentially also support
    # other types of collections.
    entries = get_entries(data_filename)

    for entry in entries:
        title = entry["title"]
        identifier = entry["id"] 
        authors = entry["author"]

        doc = xapian.Document()
        termgenerator.set_document(doc)

        termgenerator.index_text(title, 1, "S")
        termgenerator.index_text(title)

        termgenerator.increase_termpos()

        for author in authors:
            termgenerator.index_text(author, 1, "A")

        termgenerator.increase_termpos()

        # FIXME: This is for debugging purposes only: we store the full
        # entry as a nicely-formatted entry.
        doc.set_data(json.dumps(entry, indent=4))

        id_term = "Q" + identifier
        doc.add_boolean_term(id_term)
        db.replace_document(id_term, doc)

########################################################################
# HVC SVNT DRACONES
########################################################################

index_documents("/tmp/tda.bib", "data/") 
