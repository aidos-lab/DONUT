"""Main Flask module."""

import datetime

from flask import Flask
from flask import render_template
from flask import request

from dat.database import get_random_document
from dat.database import get_tags
from dat.database import search

from xapian import QueryParserError

DATABASE_DIR = "data/"


def create_app(test_config=None):
    """Create main application."""
    app = Flask(__name__)

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
        matches = get_random_document(DATABASE_DIR)
        return render_template("index.html", data=matches, duration=None)

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/tags")
    def tags():
        tags = get_tags(DATABASE_DIR)
        return render_template("tags.html", tags=sorted(tags.items()))

    return app
