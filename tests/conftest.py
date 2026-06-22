"""Shared test fixtures."""

import json
import os

import pytest
import xapian

from donut import create


@pytest.fixture
def sample_entries():
    """Return sample document entries for testing."""
    return [
        {
            "title": "Persistent Homology in Neuroscience",
            "author": ["Alice Smith", "Bob Jones"],
            "keywords": [
                ("applications", "neuroscience"),
                ("applications", "neuroscience:brain imaging"),
                ("tools", "persistent homology"),
                ("data", "point cloud"),
            ],
            "code": [],
            "data": [],
            "videos": [],
            "abstract": "We apply persistent homology to brain data.",
            "year": "2023",
            "doi": "10.1234/test1",
            "url": "",
            "id": "smith_persistent_2023",
            "type": "article",
            "raw": {
                "ID": "smith_persistent_2023",
                "ENTRYTYPE": "article",
                "title": "Persistent Homology in Neuroscience",
                "author": "Smith, Alice and Jones, Bob",
                "year": "2023",
            },
        },
        {
            "title": "Mapper for Materials Science",
            "author": ["Carol White", "Bob Jones"],
            "keywords": [
                ("applications", "materials science"),
                ("tools", "mapper"),
                ("tools", "persistent homology"),
                ("data", "point cloud"),
            ],
            "code": [],
            "data": [],
            "videos": [],
            "abstract": "Mapper applied to materials.",
            "year": "2022",
            "doi": "10.1234/test2",
            "url": "",
            "id": "white_mapper_2022",
            "type": "article",
            "raw": {
                "ID": "white_mapper_2022",
                "ENTRYTYPE": "article",
                "title": "Mapper for Materials Science",
                "author": "White, Carol and Jones, Bob",
                "year": "2022",
            },
        },
        {
            "title": "TDA in Climate Modeling",
            "author": ["David Brown"],
            "keywords": [
                ("applications", "climate science"),
                ("tools", "persistent homology"),
                ("tools", "simplicial complex"),
                ("data", "time series"),
            ],
            "code": [],
            "data": [],
            "videos": [],
            "abstract": "Climate data analyzed with TDA.",
            "year": "2024",
            "doi": "10.1234/test3",
            "url": "",
            "id": "brown_tda_2024",
            "type": "article",
            "raw": {
                "ID": "brown_tda_2024",
                "ENTRYTYPE": "article",
                "title": "TDA in Climate Modeling",
                "author": "Brown, David",
                "year": "2024",
            },
        },
        {
            "title": "GUDHI Library",
            "author": ["GUDHI Project"],
            "keywords": [
                ("tools", "persistent homology"),
                ("tools", "simplicial complex"),
            ],
            "code": [("https://github.com/GUDHI/gudhi-devel", "GitHub")],
            "data": [],
            "videos": [],
            "abstract": "Open source TDA library.",
            "year": "2024",
            "doi": "",
            "url": "https://gudhi.inria.fr/",
            "id": "gudhi_2024",
            "type": "software",
            "raw": {
                "ID": "gudhi_2024",
                "ENTRYTYPE": "software",
                "title": "GUDHI Library",
                "author": "GUDHI Project",
                "year": "2024",
            },
        },
    ]


@pytest.fixture
def test_db(sample_entries, tmp_path):
    """Create a temporary Xapian database with sample entries."""
    from donut.database import SLOT_YEAR

    db_dir = str(tmp_path / "test_db")
    db = xapian.WritableDatabase(db_dir, xapian.DB_CREATE_OR_OPEN)

    termgenerator = xapian.TermGenerator()
    termgenerator.set_database(db)
    termgenerator.set_stemmer(xapian.Stem("en"))

    for entry in sample_entries:
        doc = xapian.Document()
        termgenerator.set_document(doc)

        termgenerator.index_text(entry["title"], 1, "S")
        termgenerator.index_text(entry["title"])
        termgenerator.increase_termpos()

        for author in entry["author"]:
            termgenerator.index_text(author, 1, "A")
            termgenerator.index_text(author)
        termgenerator.increase_termpos()

        termgenerator.index_text(entry["abstract"], 1, "XA")
        termgenerator.index_text(entry["abstract"])
        termgenerator.increase_termpos()

        for _, keyword in entry["keywords"]:
            termgenerator.index_text(keyword, 1, "K")
            termgenerator.index_text(keyword)
        termgenerator.increase_termpos()

        doc.set_data(json.dumps(entry, indent=4))

        year = entry.get("year", "0000")
        doc.add_value(
            SLOT_YEAR, xapian.sortable_serialise(int(year))
        )

        id_term = "Q" + entry["id"]
        doc.add_boolean_term(id_term)
        db.replace_document(id_term, doc)

    db.close()
    return db_dir


@pytest.fixture
def app(test_db):
    """Create Flask test app pointing at the test database."""
    os.environ["DATABASE_DIR"] = test_db
    application = create()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
