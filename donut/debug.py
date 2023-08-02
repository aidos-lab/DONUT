"""Debug data base insertion.

Normally, you should not have to run this script. It was developed to
manually test the insertion of articles in the database, and to debug
their parsing process.
"""

from dotenv import load_dotenv

from donut.database import index_documents

import os

load_dotenv()


if __name__ == "__main__":
    DATABASE_DIR = os.getenv("DATABASE_DIR", "data")
    assert DATABASE_DIR is not None

    index_documents("/tmp/tda.bib", DATABASE_DIR)
