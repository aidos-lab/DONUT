"""Main Flask module."""

from flask import Flask
from flask import render_template
from flask import request

from dat.database import index_documents
from dat.database import search

DATABASE_DIR = "data/"


def create_app(test_config=None):
    app = Flask(__name__)

    # TODO: We probably should call this from somewhere else and add
    # some configuration options.
    index_documents("/tmp/tda.bib", DATABASE_DIR)

    @app.route("/", methods=["GET", "POST"])
    def index():
        data = []
        if request.form:
            matches = search(DATABASE_DIR, request.form["query"])
            data = matches

        return render_template("index.html", data=data)

    @app.route("/about")
    def about():
        return render_template("about.html")

    return app
