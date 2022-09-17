"""Main Flask module."""

from flask import Flask
from flask import render_template


def create_app(test_config=None):
    app = Flask(__name__)

    print(app.instance_path)

    @app.route("/")
    def index():
        return render_template("index.html", data=[])

    @app.route("/about")
    def about():
        return render_template("about.html")

    return app
