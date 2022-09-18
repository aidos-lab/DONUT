"""Update data base by querying Zotero items.

The purpose of this script is to query the online Zotero database,
download all items, and update the local database accordingly. The
benefit of this approach is that, as time progresses, more fields,
such as tags, can be easily accommodated.
"""

from dotenv import load_dotenv
from pyzotero import zotero

from dat.database import index_documents

import bibtexparser
import os
import tempfile

load_dotenv()


if __name__ == "__main__":
    API_KEY = os.getenv("ZOTERO_API_KEY")
    DATABASE_DIR = os.getenv("DATABASE_DIR")

    assert API_KEY is not None
    assert DATABASE_DIR is not None

    zot = zotero.Zotero(2425412, "group", API_KEY)
    zot.add_parameters(format="bibtex")

    # This returns a database compatible with `bibtexparser`. We store
    # it in a new file on purpose in order to employ our parser rather
    # than relying on an existing one.
    database = zot.everything(zot.items())

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "tda.bib")

        with open(path, "w") as f:
            bibtexparser.dump(database, f)

        index_documents(path, DATABASE_DIR)
