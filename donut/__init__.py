"""Main Flask module."""

import datetime
import io
import os
import subprocess

from dotenv import load_dotenv

from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from flask import Flask
from flask import render_template
from flask import request
from flask import send_file

from donut.database import get_document
from donut.database import get_documents
from donut.database import get_num_documents
from donut.database import get_random_document
from donut.database import get_tags
from donut.database import search

from donut.utils import flat_tags_to_hierarchy

from xapian import QueryParserError

# Make sure that we have access to the database directory and other
# information that we require.
load_dotenv()
DATABASE_DIR = os.getenv("DATABASE_DIR", "data")


def get_git_revision():
    """Return git short revision string."""
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )


def create(test_config=None):
    """Create main application."""
    app = Flask(__name__)
    app.jinja_env.globals.update(get_git_revision=get_git_revision)
    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    @app.route("/", methods=["GET", "POST"])
    def index():
        num_documents = get_num_documents(DATABASE_DIR)
        start = datetime.datetime.now()

        if request.method == "POST":
            query = request.form["query"]
        else:
            query = request.args.get("q", "")

        try:
            matches = search(DATABASE_DIR, query)
        except QueryParserError:
            return render_template("error.html", query=query)

        if matches:
            duration = datetime.datetime.now() - start
            duration = duration.total_seconds()
        else:
            duration = None

        return render_template(
            "index.html",
            data=matches[0] if matches else None,
            query=query,
            suggestion=matches[1] if matches else "",
            num_documents=num_documents,
            duration=duration,
        )

    @app.route("/papers")
    def papers():
        start = datetime.datetime.now()

        matches = get_documents(DATABASE_DIR)

        matches = [
            m
            for m in matches
            if m["document"]["raw"]["ENTRYTYPE"] != "software"
        ]

        duration = datetime.datetime.now() - start
        duration = duration.total_seconds()

        return render_template(
            "index.html",
            data=matches,
            duration=duration,
        )

    @app.route("/software")
    def software():
        start = datetime.datetime.now()

        matches = get_documents(DATABASE_DIR)

        matches = [
            m
            for m in matches
            if m["document"]["raw"]["ENTRYTYPE"] == "software"
        ]

        duration = datetime.datetime.now() - start
        duration = duration.total_seconds()

        return render_template(
            "index.html",
            data=matches,
            duration=duration,
        )

    @app.route("/random", methods=["POST"])
    def random():
        matches = [get_random_document(DATABASE_DIR)]
        return render_template("index.html", data=matches, duration=None)

    @app.route("/faq")
    def faq():
        return render_template("faq.html")

    @app.route("/contributors")
    def contributors():
        return render_template("contributors.html")

    @app.route("/tags")
    def tags():
        tags = get_tags(DATABASE_DIR)

        tags = {
            category: sorted(keywords.items())
            for category, keywords in sorted(tags.items())
        }

        tags = flat_tags_to_hierarchy(tags)
        return render_template("tags.html", tags=tags)

    @app.route("/export/<int:identifier>")
    def export(identifier):
        document = get_document(DATABASE_DIR, identifier)

        # Prepare document for export by renaming some of the keys. Not
        # a big fan of this, but it's easier than storing everything.

        db = BibDatabase()
        db.entries = [document["document"]["raw"]]

        writer = BibTexWriter()
        buffer = io.BytesIO()
        buffer.write(writer.write(db).encode())
        buffer.seek(0)

        name = document["document"]["raw"]["ID"] + ".bib"

        return send_file(
            buffer,
            as_attachment=True,
            download_name=name,
            mimetype="application/x-bibtex",
        )

    return app
