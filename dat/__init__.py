"""Main Flask module."""

from flask import Flask
from flask import render_template
from flask import request

from dat.database import get_document
from dat.database import search

DATABASE_DIR = "data/"


def create_app(test_config=None):
    app = Flask(__name__)

    @app.route("/", methods=["GET", "POST"])
    def index():
        data = None
        query = None

        if request.form:
            query = request.form["query"]
            matches = search(DATABASE_DIR, request.form["query"])
            data = matches

        return render_template("index.html", data=data, query=query)

    @app.route("/view/<int:identifier>/", methods=["GET"])
    def view(identifier):
        document = get_document(DATABASE_DIR, identifier)
        return render_template("view.html", document=document)


    @app.route("/about")
    def about():
        return render_template("about.html")

    return app
