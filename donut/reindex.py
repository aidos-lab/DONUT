"""Reindex all documents in the database.

This script can be called at all times. It will perform a new indexing
operation on all `.bib` files stored in the `data` directory.
"""


from dotenv import load_dotenv

from donut.database import index_documents

import glob
import os

load_dotenv()


if __name__ == "__main__":
    DATA_DIR = os.getenv("DATA_DIR", "data")
    DATABASE_DIR = os.getenv("DATABASE_DIR", "database")

    assert DATA_DIR is not None
    assert DATABASE_DIR is not None

    filenames = glob.glob(os.path.join(DATA_DIR, "*.bib"))

    for filename in filenames:
        index_documents(filename, DATABASE_DIR)
