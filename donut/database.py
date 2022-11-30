"""Database module."""

import collections
import json
import random
import unidecode
import xapian

from donut.parse_bibtex import get_entries


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
            termgenerator.index_text(author)

            # Make sure that we can properly handle authors whose names
            # include accents.
            author_normalised = unidecode.unidecode(author)
            if author != author_normalised:
                termgenerator.index_text(author_normalised, 1, "A")
                termgenerator.index_text(author_normalised)

        termgenerator.increase_termpos()

        abstract = entry["abstract"]

        termgenerator.index_text(abstract, 1, "XA")
        termgenerator.index_text(abstract)

        termgenerator.increase_termpos()

        # We deliberately ignore any categories here. The categories
        # will only be relevant for rendering later on.
        for _, keyword in entry["keywords"]:
            termgenerator.index_text(keyword, 1, "K")
            termgenerator.index_text(keyword)

        termgenerator.increase_termpos()

        # FIXME: This is for debugging purposes only: we store the full
        # entry as a nicely-formatted object.
        doc.set_data(json.dumps(entry, indent=4))

        id_term = "Q" + identifier
        doc.add_boolean_term(id_term)
        db.replace_document(id_term, doc)


def _build_match(document):
    """Build match from document."""
    identifier = document.get_docid()
    data = json.loads(document.get_data())
    return {"id": identifier, "document": data}


def search(database_dir, query_str):
    """Search data base with given query string.

    Parameters
    ----------
    database_dir : str
        Directory of database

    query_str : str or None
        String to search database for. If `None`, the method will return
        `None` as well.

    Returns
    -------
    List of dict or None
        Matches corresponding to the query or `None`, if no query string was
        provided.
    """
    # Being explicit here: whether the string is empty or `None`, we
    # will always return *no* matches.
    if query_str is None or query_str == "":
        return None

    db = xapian.Database(database_dir)

    queryparser = xapian.QueryParser()
    queryparser.set_stemmer(xapian.Stem("en"))
    queryparser.set_stemming_strategy(queryparser.STEM_SOME)

    queryparser.add_prefix("title", "S")
    queryparser.add_prefix("author", "A")
    queryparser.add_prefix("abstract", "XA")
    queryparser.add_prefix("tag", "K")
    queryparser.add_prefix("keyword", "K")

    query = queryparser.parse_query(query_str)

    enquire = xapian.Enquire(db)
    enquire.set_query(query)

    # TODO: Potential bottleneck if the database grows very large. Maybe
    # we should rather add some pagination here?
    n_documents = db.get_doccount()

    matches = []
    for match in enquire.get_mset(0, n_documents):
        matches.append(_build_match(match.document))

    matches = sorted(
        matches, key=lambda x: x["document"]["year"], reverse=True
    )

    return matches


def get_document(database_dir, identifier):
    """Return specific document from database."""
    db = xapian.Database(database_dir)
    document = db.get_document(identifier)

    return _build_match(document)


def get_random_document(database_dir):
    """Return random document from database."""
    db = xapian.Database(database_dir)
    identifier = random.randint(1, db.get_lastdocid())
    document = db.get_document(identifier)

    return _build_match(document)


def get_tags(database_dir):
    """Return all tags of all documents.

    Returns
    -------
    dict of counters
        The outer dictionary will contain the overall tag categories,
        such as "applications", whereas each value of the dictionary
        will be a counter with the respective tags.
    """
    db = xapian.Database(database_dir)
    tags = collections.defaultdict(collections.Counter)

    for item in db.postlist(""):
        identifier = item.docid
        document = db.get_document(identifier)
        data = json.loads(document.get_data())

        for category, keyword in data["keywords"]:
            tags[category][keyword.lower()] += 1

    return tags
