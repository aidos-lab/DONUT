"""Main Flask module."""

import datetime

from flask import Flask
from flask import render_template
from flask import request

from dat.database import get_document
from dat.database import search

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

        matches = search(DATABASE_DIR, query)
        data = matches

        if matches:
            duration = datetime.datetime.now() - start
            duration = duration.total_seconds()
        else:
            duration = None

        return render_template(
            "index.html",
            data=data,
            query=query,
            duration=duration,
        )

    @app.route("/view/<int:identifier>/", methods=["GET"])
    def view(identifier):
        document = get_document(DATABASE_DIR, identifier)
        return render_template("view.html", document=document)

    @app.route("/about")
    def about():
        return render_template("about.html")

    return app
