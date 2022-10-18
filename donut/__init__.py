"""Main Flask module."""

import datetime
import io
import subprocess

from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from flask import Flask
from flask import render_template
from flask import request
from flask import send_file

from donut.database import get_document
from donut.database import get_random_document
from donut.database import get_tags
from donut.database import search

from xapian import QueryParserError

DATABASE_DIR = "data/"


def get_git_revision():
    """Return git short revision string."""
    return (
        subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
        .decode("ascii")
        .strip()
    )


def create_app(test_config=None):
    """Create main application."""
    app = Flask(__name__)
    app.jinja_env.globals.update(get_git_revision=get_git_revision)

    @app.route("/", methods=["GET", "POST"])
    def index():
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
            data=matches,
            query=query,
            duration=duration,
        )

    @app.route("/random", methods=["POST"])
    def random():
        matches = [get_random_document(DATABASE_DIR)]
        return render_template("index.html", data=matches, duration=None)

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/tags")
    def tags():
        tags = get_tags(DATABASE_DIR)

        tags = {
            category: sorted(keywords.items())
            for category, keywords in sorted(tags.items())
        }

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
