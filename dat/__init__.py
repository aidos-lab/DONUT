"""Main Flask module."""

from flask import Flask


def create_app(test_config=None):
    app = Flask(__name__)

    print(app.instance_path)

    @app.route('/')
    def index():
        return 'Hello, World!'

    return app
