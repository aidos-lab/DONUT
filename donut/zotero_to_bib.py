"""Convert Zotero database to `.bib` files.

The purpose of this script is to query the online Zotero database,
download all items, and convert them to `.bib` files, which can be
stored and managed via `git`.
"""

from dotenv import load_dotenv
from pyzotero import zotero

import bibtexparser
import os

load_dotenv()


if __name__ == "__main__":
    API_KEY = os.getenv("ZOTERO_API_KEY")
    DATA_DIR = os.getenv("DATA_DIR", "data")

    assert API_KEY is not None
    assert DATA_DIR is not None

    zot = zotero.Zotero(2425412, "group", API_KEY)
    zot.add_parameters(format="biblatex")

    database = zot.everything(zot.items())

    for entry in database.entries:
        database_ = bibtexparser.bibdatabase.BibDatabase()
        database_.entries = [entry]

        assert "ID" in entry

        filename = entry["ID"].strip().lower()
        filename = os.path.join(DATA_DIR, filename + ".bib")

        with open(filename, "w") as f:
            bibtexparser.dump(database_, f)
