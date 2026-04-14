"""Main Flask module."""

import collections
import datetime
import io
import json as _json
import os
import subprocess
import time

from dotenv import load_dotenv

from bibtexparser.bwriter import BibTexWriter
from bibtexparser.bibdatabase import BibDatabase

from flask import Flask
from flask import flash
from flask import jsonify
from flask import redirect
from flask import render_template
from flask import request
from flask import send_file
from flask import url_for

from donut.database import compute_facets
from donut.database import get_document
from donut.database import get_documents
from donut.database import get_num_documents
from donut.database import get_random_document
from donut.database import get_tags
from donut.database import search
from donut.database import PAGE_SIZE

from xapian import QueryParserError

# Make sure that we have access to the database directory and other
# information that we require.
load_dotenv()
DATABASE_DIR = os.getenv("DATABASE_DIR", "database")


def _load_json_file(path):
    """Load a JSON file if it exists, otherwise return empty."""
    if os.path.exists(path):
        with open(path) as f:
            return _json.load(f)
    return {}


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
    app.secret_key = os.getenv(
        "SECRET_KEY", "donut-dev-key-change-in-production"
    )

    similarity_data = _load_json_file(
        os.path.join(DATABASE_DIR, "similarity.json")
    )

    @app.route("/", methods=["GET", "POST"])
    def index():
        num_documents = get_num_documents(DATABASE_DIR)
        start = datetime.datetime.now()

        if request.method == "POST":
            query = request.form["query"]
        else:
            query = request.args.get("q", "")

        sort = request.args.get("sort", "")
        page = request.args.get("page", 1, type=int)

        sort_by = None
        reverse = True
        if sort == "year_desc":
            sort_by = "year"
            reverse = True
        elif sort == "year_asc":
            sort_by = "year"
            reverse = False

        offset = (page - 1) * PAGE_SIZE

        try:
            matches = search(
                DATABASE_DIR, query, sort_by=sort_by,
                reverse=reverse, offset=offset, limit=PAGE_SIZE,
            )
        except QueryParserError:
            return render_template("error.html", query=query)

        if matches:
            duration = datetime.datetime.now() - start
            duration = duration.total_seconds()
            facets = compute_facets(matches[0])
        else:
            duration = None
            facets = None

        return render_template(
            "index.html",
            data=matches[0] if matches else None,
            query=query,
            suggestion=matches[1] if matches else "",
            num_documents=num_documents,
            duration=duration,
            sort=sort,
            page=page,
            facets=facets,
            related=similarity_data,
        )

    @app.route("/papers")
    def papers():
        start = datetime.datetime.now()

        page = request.args.get("page", 1, type=int)
        sort = request.args.get("sort", "year_desc")
        offset = (page - 1) * PAGE_SIZE

        matches = get_documents(
            DATABASE_DIR, offset=offset, limit=PAGE_SIZE,
            entry_type="article",
        )

        total = get_num_documents(DATABASE_DIR)
        total_pages = max(1, (total // PAGE_SIZE) + 1)

        duration = datetime.datetime.now() - start
        duration = duration.total_seconds()

        return render_template(
            "index.html",
            data=matches,
            duration=duration,
            page=page,
            total_pages=total_pages,
            sort=sort,
            related=similarity_data,
        )

    @app.route("/software")
    def software():
        start = datetime.datetime.now()

        page = request.args.get("page", 1, type=int)
        offset = (page - 1) * PAGE_SIZE

        matches = get_documents(
            DATABASE_DIR, offset=offset, limit=PAGE_SIZE,
            entry_type="software",
        )

        total = get_num_documents(DATABASE_DIR)
        total_pages = max(1, (total // PAGE_SIZE) + 1)

        duration = datetime.datetime.now() - start
        duration = duration.total_seconds()

        return render_template(
            "index.html",
            data=matches,
            duration=duration,
            page=page,
            total_pages=total_pages,
            sort="",
            related=similarity_data,
        )

    @app.route("/random", methods=["POST"])
    def random():
        matches = [get_random_document(DATABASE_DIR)]
        return render_template(
            "index.html", data=matches, duration=None,
            related=similarity_data,
        )

    @app.route("/faq")
    def faq():
        return render_template("faq.html")

    @app.route("/contributors")
    def contributors():
        return render_template("contributors.html")

    @app.route("/tags")
    def tags():
        raw_tags = get_tags(DATABASE_DIR)

        # Build a flat list of (keyword, count, category) sorted
        # alphabetically by keyword for the combined view.
        all_tags = []
        categories = sorted(raw_tags.keys())
        for category in categories:
            for keyword, count in raw_tags[category].items():
                all_tags.append((keyword, count, category))
        all_tags.sort(key=lambda t: t[0].lower())

        return render_template(
            "tags.html",
            all_tags=all_tags,
            categories=categories,
        )

    @app.route("/export/<int:identifier>")
    def export(identifier):
        document = get_document(DATABASE_DIR, identifier)

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

    @app.route("/export-all")
    def export_all():
        """Export all papers matching current query as .bib file."""
        query = request.args.get("q", "")

        if query:
            try:
                result = search(
                    DATABASE_DIR, query, limit=10000
                )
                data = result[0] if result else []
            except QueryParserError:
                data = []
        else:
            data = get_documents(DATABASE_DIR)

        db = BibDatabase()
        db.entries = [m["document"]["raw"] for m in data]

        writer = BibTexWriter()
        buffer = io.BytesIO()
        buffer.write(writer.write(db).encode())
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="donut-export.bib",
            mimetype="application/x-bibtex",
        )

    @app.route("/stats")
    def stats():
        from donut.analysis import compute_statistics
        statistics = compute_statistics(DATABASE_DIR)
        return render_template("stats.html", stats=statistics)

    @app.route("/explore")
    def explore():
        cooccurrence_path = os.path.join(
            DATABASE_DIR, "cooccurrence.json"
        )
        if os.path.exists(cooccurrence_path):
            with open(cooccurrence_path) as f:
                edges = _json.load(f)
        else:
            from donut.analysis import compute_tag_cooccurrence
            edges = compute_tag_cooccurrence(DATABASE_DIR)

        tag_data = get_tags(DATABASE_DIR)
        tag_counts = {}
        for category_tags in tag_data.values():
            for tag, count in category_tags.items():
                tag_counts[tag] = count

        return render_template(
            "explore.html", edges=edges, tag_counts=tag_counts,
        )

    @app.route("/api/tag-cooccurrence")
    def api_tag_cooccurrence():
        cooccurrence_path = os.path.join(
            DATABASE_DIR, "cooccurrence.json"
        )
        if os.path.exists(cooccurrence_path):
            with open(cooccurrence_path) as f:
                edges = _json.load(f)
        else:
            from donut.analysis import compute_tag_cooccurrence
            edges = compute_tag_cooccurrence(DATABASE_DIR)
        return jsonify(edges)

    @app.route("/timeline")
    def timeline():
        matches = get_documents(DATABASE_DIR)
        papers_list = [
            m for m in matches
            if m["document"]["raw"]["ENTRYTYPE"] != "software"
        ]

        by_year = collections.defaultdict(list)
        for p in papers_list:
            doc = p["document"]
            year = doc.get("year", "unknown")
            app_tags = [
                kw for cat, kw in doc.get("keywords", [])
                if cat == "applications"
            ]
            primary_tag = (
                app_tags[0] if app_tags else "untagged"
            )
            by_year[year].append({
                "title": doc["title"],
                "tag": primary_tag,
                "id": p["id"],
            })

        by_year = dict(sorted(by_year.items()))
        return render_template("timeline.html", by_year=by_year)

    @app.route("/submit", methods=["GET", "POST"])
    def submit():
        tag_data = get_tags(DATABASE_DIR)

        all_tags = {}
        for category, keywords in tag_data.items():
            all_tags[category] = sorted(keywords.keys())

        if request.method == "POST":
            tags_applications = request.form.getlist(
                "tags_applications"
            )
            tags_tools = request.form.getlist("tags_tools")
            tags_data = request.form.getlist("tags_data")
            flavour = request.form.get("flavour", "")

            # Build Zotero-format keywords so a future push
            # can use them directly.
            zotero_keywords = (
                [f"1 - {t}" for t in tags_applications]
                + [f"2 - {t}" for t in tags_tools]
                + [f"3 - {t}" for t in tags_data]
            )
            if flavour:
                zotero_keywords.append(flavour)

            submission = {
                "status": "pending",
                "submitted_at": datetime.datetime.utcnow()
                    .isoformat() + "Z",
                "title": request.form.get("title", "").strip(),
                "authors": request.form.get(
                    "authors", ""
                ).strip(),
                "year": request.form.get("year", "").strip(),
                "doi": request.form.get("doi", "").strip(),
                "url": request.form.get("url", "").strip(),
                "abstract": request.form.get(
                    "abstract", ""
                ).strip(),
                "entry_type": request.form.get(
                    "entry_type", "article"
                ),
                "tags_applications": tags_applications,
                "tags_tools": tags_tools,
                "tags_data": tags_data,
                "zotero_keywords": zotero_keywords,
                "new_tags": request.form.get(
                    "new_tags", ""
                ).strip(),
                "flavour": flavour,
                "code_url": request.form.get(
                    "code_url", ""
                ).strip(),
                "data_url": request.form.get(
                    "data_url", ""
                ).strip(),
                "video_url": request.form.get(
                    "video_url", ""
                ).strip(),
            }

            errors = []
            if not submission["title"]:
                errors.append("Title is required.")
            if not submission["authors"]:
                errors.append("At least one author is required.")
            if not submission["year"]:
                errors.append("Year is required.")
            if (not submission["doi"]
                    and not submission["url"]):
                errors.append("DOI or URL is required.")

            if errors:
                return render_template(
                    "submit.html",
                    tags=all_tags,
                    errors=errors,
                    form=submission,
                )

            submissions_dir = os.path.join(
                os.path.dirname(DATABASE_DIR), "submissions"
            )
            os.makedirs(submissions_dir, exist_ok=True)

            filename = (
                f"{int(time.time())}_"
                f"{submission['title'][:40]}.json"
            )
            filename = "".join(
                c if c.isalnum() or c in "._-"
                else "_" for c in filename
            )
            filepath = os.path.join(submissions_dir, filename)

            with open(filepath, "w") as f:
                _json.dump(submission, f, indent=2)

            flash(
                "Thank you! Your submission has been received "
                "and will be reviewed by a maintainer."
            )
            return redirect(url_for("submit"))

        return render_template(
            "submit.html", tags=all_tags, errors=[], form={},
        )

    return app
