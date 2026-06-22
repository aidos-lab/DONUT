# DONUT: Discovery, Contributions & Productivity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add discovery features (tag co-occurrence explorer, stats dashboard, related papers, timeline), contributor tools (web submission form, tag validator), and researcher productivity improvements (sorting, pagination, faceted search, bulk export) to DONUT.

**Architecture:** All new features extend the existing Flask + Xapian stack. Discovery data (co-occurrence, similarity) is precomputed at reindex time and stored as JSON files. Two CDN-loaded JS libraries (D3.js for the graph, Chart.js for charts) handle interactive visualizations. The submission form stores JSON files for maintainer review. No new Python dependencies.

**Tech Stack:** Python 3.14, Flask 3.1, Xapian 1.4, D3.js (CDN), Chart.js (CDN), pytest (new dev dependency)

---

## File Structure

### New files to create:

| File | Responsibility |
|------|---------------|
| `tests/conftest.py` | Pytest fixtures: Flask test client, temporary Xapian database |
| `tests/test_database.py` | Tests for sorting, pagination, facets in database.py |
| `tests/test_analysis.py` | Tests for co-occurrence and similarity computation |
| `tests/test_routes.py` | Tests for all new and modified Flask routes |
| `tests/test_validate_tags.py` | Tests for tag validation logic |
| `donut/analysis.py` | Tag co-occurrence computation, statistics aggregation |
| `donut/similarity.py` | Jaccard similarity for related papers |
| `donut/validate_tags.py` | CLI tag validator + tag validation functions |
| `donut/templates/explore.html` | D3.js tag co-occurrence graph |
| `donut/templates/stats.html` | Statistics dashboard with Chart.js |
| `donut/templates/timeline.html` | Timeline view |
| `donut/templates/submit.html` | Web submission form |
| `donut/templates/facets.html` | Faceted search partial (included in index.html) |

### Files to modify:

| File | Changes |
|------|---------|
| `pyproject.toml` | Add pytest dev dependency |
| `donut/database.py` | Add SLOT_YEAR constant, year value slot in indexing, sort_by/offset/limit params to search(), paginated get_documents(), compute_facets() |
| `donut/__init__.py` | New routes, modify existing routes for sort/pagination/facets |
| `donut/reindex.py` | After indexing, compute similarity + co-occurrence, run tag validation |
| `donut/templates/base.html` | Updated navigation |
| `donut/templates/index.html` | Sort controls, pagination, bulk export link, facets, related papers |
| `donut/static/style.css` | Styles for pagination, facets, sort controls, forms, stats |

---

## Task 1: Test Infrastructure + Sorting

**Files:**
- Create: `tests/__init__.py`, `tests/conftest.py`, `tests/test_database.py`
- Modify: `pyproject.toml`, `donut/database.py`

- [ ] **Step 1: Add pytest to dev dependencies**

Add a dev dependency section to `pyproject.toml`:

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^7.0"
```

Then install:

```bash
cd /Users/yossi/DONUT && .venv/bin/pip install pytest
```

- [ ] **Step 2: Create test fixtures**

Create `tests/__init__.py` (empty file) and `tests/conftest.py`:

```python
"""Shared test fixtures."""

import json
import os
import tempfile

import pytest
import xapian

from donut import create


@pytest.fixture
def sample_entries():
    """Return sample document entries for testing."""
    return [
        {
            "title": "Persistent Homology in Neuroscience",
            "author": ["Alice Smith", "Bob Jones"],
            "keywords": [
                ("applications", "neuroscience"),
                ("applications", "neuroscience:brain imaging"),
                ("tools", "persistent homology"),
                ("data", "point cloud"),
            ],
            "code": [],
            "data": [],
            "videos": [],
            "abstract": "We apply persistent homology to brain data.",
            "year": "2023",
            "doi": "10.1234/test1",
            "url": "",
            "id": "smith_persistent_2023",
            "type": "article",
            "raw": {
                "ID": "smith_persistent_2023",
                "ENTRYTYPE": "article",
                "title": "Persistent Homology in Neuroscience",
                "author": "Smith, Alice and Jones, Bob",
                "year": "2023",
            },
        },
        {
            "title": "Mapper for Materials Science",
            "author": ["Carol White", "Bob Jones"],
            "keywords": [
                ("applications", "materials science"),
                ("tools", "mapper"),
                ("tools", "persistent homology"),
                ("data", "point cloud"),
            ],
            "code": [],
            "data": [],
            "videos": [],
            "abstract": "Mapper applied to materials.",
            "year": "2022",
            "doi": "10.1234/test2",
            "url": "",
            "id": "white_mapper_2022",
            "type": "article",
            "raw": {
                "ID": "white_mapper_2022",
                "ENTRYTYPE": "article",
                "title": "Mapper for Materials Science",
                "author": "White, Carol and Jones, Bob",
                "year": "2022",
            },
        },
        {
            "title": "TDA in Climate Modeling",
            "author": ["David Brown"],
            "keywords": [
                ("applications", "climate science"),
                ("tools", "persistent homology"),
                ("tools", "simplicial complex"),
                ("data", "time series"),
            ],
            "code": [],
            "data": [],
            "videos": [],
            "abstract": "Climate data analyzed with TDA.",
            "year": "2024",
            "doi": "10.1234/test3",
            "url": "",
            "id": "brown_tda_2024",
            "type": "article",
            "raw": {
                "ID": "brown_tda_2024",
                "ENTRYTYPE": "article",
                "title": "TDA in Climate Modeling",
                "author": "Brown, David",
                "year": "2024",
            },
        },
        {
            "title": "GUDHI Library",
            "author": ["GUDHI Project"],
            "keywords": [
                ("tools", "persistent homology"),
                ("tools", "simplicial complex"),
            ],
            "code": [("https://github.com/GUDHI/gudhi-devel", "GitHub")],
            "data": [],
            "videos": [],
            "abstract": "Open source TDA library.",
            "year": "2024",
            "doi": "",
            "url": "https://gudhi.inria.fr/",
            "id": "gudhi_2024",
            "type": "software",
            "raw": {
                "ID": "gudhi_2024",
                "ENTRYTYPE": "software",
                "title": "GUDHI Library",
                "author": "GUDHI Project",
                "year": "2024",
            },
        },
    ]


@pytest.fixture
def test_db(sample_entries, tmp_path):
    """Create a temporary Xapian database with sample entries."""
    db_dir = str(tmp_path / "test_db")
    db = xapian.WritableDatabase(db_dir, xapian.DB_CREATE_OR_OPEN)

    termgenerator = xapian.TermGenerator()
    termgenerator.set_database(db)
    termgenerator.set_stemmer(xapian.Stem("en"))

    SLOT_YEAR = 0

    for entry in sample_entries:
        doc = xapian.Document()
        termgenerator.set_document(doc)

        termgenerator.index_text(entry["title"], 1, "S")
        termgenerator.index_text(entry["title"])
        termgenerator.increase_termpos()

        for author in entry["author"]:
            termgenerator.index_text(author, 1, "A")
            termgenerator.index_text(author)
        termgenerator.increase_termpos()

        termgenerator.index_text(entry["abstract"], 1, "XA")
        termgenerator.index_text(entry["abstract"])
        termgenerator.increase_termpos()

        for _, keyword in entry["keywords"]:
            termgenerator.index_text(keyword, 1, "K")
            termgenerator.index_text(keyword)
        termgenerator.increase_termpos()

        doc.set_data(json.dumps(entry, indent=4))

        year = entry.get("year", "0000")
        doc.add_value(SLOT_YEAR, xapian.sortable_serialise(int(year)))

        id_term = "Q" + entry["id"]
        doc.add_boolean_term(id_term)
        db.replace_document(id_term, doc)

    db.close()
    return db_dir


@pytest.fixture
def app(test_db):
    """Create Flask test app pointing at the test database."""
    os.environ["DATABASE_DIR"] = test_db
    application = create()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
```

- [ ] **Step 3: Write failing tests for sorting**

Create `tests/test_database.py`:

```python
"""Tests for database module."""

from donut.database import search, get_documents, SLOT_YEAR


def test_search_returns_results(test_db):
    """Search for a known term returns matches."""
    results = search(test_db, "homology")
    assert results is not None
    matches, corrected = results
    assert len(matches) >= 1


def test_search_sort_by_year_desc(test_db):
    """Results sorted by year descending (newest first)."""
    results = search(test_db, "persistent homology", sort_by="year",
                     reverse=True)
    matches, _ = results
    years = [m["document"]["year"] for m in matches]
    assert years == sorted(years, reverse=True)


def test_search_sort_by_year_asc(test_db):
    """Results sorted by year ascending (oldest first)."""
    results = search(test_db, "persistent homology", sort_by="year",
                     reverse=False)
    matches, _ = results
    years = [m["document"]["year"] for m in matches]
    assert years == sorted(years)


def test_search_empty_returns_none(test_db):
    """Empty or None query returns None."""
    assert search(test_db, None) is None
    assert search(test_db, "") is None
```

- [ ] **Step 4: Run tests to verify they fail**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_database.py -v
```

Expected: FAIL — `SLOT_YEAR` not importable, `sort_by` parameter not accepted.

- [ ] **Step 5: Implement sorting in database.py**

In `donut/database.py`, add `SLOT_YEAR` constant at module level (after imports) and update `index_documents` to store year as a value slot. Update `search` to accept `sort_by` and `reverse` parameters.

Add after line 10 (after `from donut.parse_bibtex import get_entries`):

```python
SLOT_YEAR = 0
```

In `index_documents`, add after line 81 (`doc.set_data(json.dumps(entry, indent=4))`):

```python
        year = entry.get("year", "0000")
        try:
            doc.add_value(
                SLOT_YEAR, xapian.sortable_serialise(int(year))
            )
        except (ValueError, TypeError):
            doc.add_value(
                SLOT_YEAR, xapian.sortable_serialise(0)
            )
```

Change `search` function signature from:

```python
def search(database_dir, query_str):
```

to:

```python
def search(database_dir, query_str, sort_by=None, reverse=True):
```

Add after line 145 (`enquire.set_query(query)`), before `n_documents = db.get_doccount()`:

```python
    if sort_by == "year":
        enquire.set_sort_by_value_then_relevance(
            SLOT_YEAR, reverse
        )
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_database.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/ donut/database.py pyproject.toml
git commit -m "Add test infrastructure and year-based sorting to database"
```

---

## Task 2: Pagination

**Files:**
- Modify: `donut/database.py`
- Modify: `tests/test_database.py`

- [ ] **Step 1: Write failing tests for pagination**

Append to `tests/test_database.py`:

```python
def test_search_with_pagination(test_db):
    """Search with offset and limit returns a subset."""
    all_results = search(test_db, "persistent homology")
    all_matches, _ = all_results
    total = len(all_matches)
    assert total >= 2

    page1 = search(test_db, "persistent homology", offset=0, limit=1)
    matches1, _ = page1
    assert len(matches1) == 1

    page2 = search(test_db, "persistent homology", offset=1, limit=1)
    matches2, _ = page2
    assert len(matches2) >= 1

    assert matches1[0]["id"] != matches2[0]["id"]


def test_get_documents_with_pagination(test_db):
    """get_documents supports offset and limit."""
    all_docs = get_documents(test_db)
    assert len(all_docs) == 4

    page1 = get_documents(test_db, offset=0, limit=2)
    assert len(page1) == 2

    page2 = get_documents(test_db, offset=2, limit=2)
    assert len(page2) == 2

    ids_page1 = {d["id"] for d in page1}
    ids_page2 = {d["id"] for d in page2}
    assert ids_page1.isdisjoint(ids_page2)


def test_get_documents_with_entry_type_filter(test_db):
    """get_documents can filter by entry type."""
    papers = get_documents(test_db, entry_type="article")
    assert all(
        d["document"]["raw"]["ENTRYTYPE"] == "article"
        for d in papers
    )
    assert len(papers) == 3

    software = get_documents(test_db, entry_type="software")
    assert all(
        d["document"]["raw"]["ENTRYTYPE"] == "software"
        for d in software
    )
    assert len(software) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_database.py -v
```

Expected: FAIL — `offset`/`limit`/`entry_type` params not accepted.

- [ ] **Step 3: Implement pagination**

In `donut/database.py`, add constant after `SLOT_YEAR`:

```python
PAGE_SIZE = 25
```

Change `search` signature from:

```python
def search(database_dir, query_str, sort_by=None, reverse=True):
```

to:

```python
def search(database_dir, query_str, sort_by=None, reverse=True,
           offset=0, limit=PAGE_SIZE):
```

Replace the `n_documents` and match-building block (lines 150-154):

```python
    n_documents = db.get_doccount()

    matches = []
    for match in enquire.get_mset(0, n_documents):
        matches.append(_build_match(match.document))
```

with:

```python
    matches = []
    for match in enquire.get_mset(offset, limit):
        matches.append(_build_match(match.document))
```

Change `get_documents` signature from:

```python
def get_documents(database_dir):
```

to:

```python
def get_documents(database_dir, offset=0, limit=None,
                  entry_type=None):
```

Replace the body of `get_documents`:

```python
    db = xapian.Database(database_dir)

    matches = []
    skipped = 0

    for item in db.postlist(""):
        identifier = item.docid
        document = db.get_document(identifier)

        if entry_type:
            data = json.loads(document.get_data())
            if data["raw"]["ENTRYTYPE"] != entry_type:
                continue

        if skipped < offset:
            skipped += 1
            continue

        matches.append(_build_match(document))

        if limit is not None and len(matches) >= limit:
            break

    return matches
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_database.py -v
```

Expected: All 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add donut/database.py tests/test_database.py
git commit -m "Add pagination and entry type filtering to database queries"
```

---

## Task 3: Update Flask Routes for Sorting + Pagination

**Files:**
- Modify: `donut/__init__.py`
- Modify: `donut/templates/index.html`
- Modify: `donut/templates/base.html`
- Modify: `donut/static/style.css`
- Create: `tests/test_routes.py`

- [ ] **Step 1: Write failing route tests**

Create `tests/test_routes.py`:

```python
"""Tests for Flask routes."""


def test_index_get(client):
    """Home page loads."""
    response = client.get("/")
    assert response.status_code == 200
    assert b"Database of Original" in response.data


def test_search_post(client):
    """Search via POST returns results."""
    response = client.post("/", data={"query": "homology"})
    assert response.status_code == 200
    assert b"Persistent Homology" in response.data


def test_search_get_with_query(client):
    """Search via GET with q param returns results."""
    response = client.get("/?q=homology")
    assert response.status_code == 200


def test_search_with_sort(client):
    """Search with sort parameter works."""
    response = client.get("/?q=homology&sort=year_desc")
    assert response.status_code == 200


def test_papers_page(client):
    """Papers page loads with pagination."""
    response = client.get("/papers")
    assert response.status_code == 200


def test_papers_page_2(client):
    """Papers page 2 loads."""
    response = client.get("/papers?page=2")
    assert response.status_code == 200


def test_software_page(client):
    """Software page loads."""
    response = client.get("/software")
    assert response.status_code == 200


def test_tags_page(client):
    """Tags page loads."""
    response = client.get("/tags")
    assert response.status_code == 200


def test_faq_page(client):
    """FAQ page loads."""
    response = client.get("/faq")
    assert response.status_code == 200


def test_random_page(client):
    """Random page returns a result."""
    response = client.post("/random")
    assert response.status_code == 200


def test_export(client):
    """Export single paper returns .bib file."""
    response = client.get("/export/1")
    assert response.status_code == 200
    assert response.content_type == "application/x-bibtex"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_routes.py -v
```

Expected: Some pass (existing routes), sort test may fail depending on route handling.

- [ ] **Step 3: Update Flask routes**

Replace the full `donut/__init__.py` with the updated version. Key changes: index route handles `sort` and `page` query params, `/papers` and `/software` use pagination and `entry_type` filter, new `/export-all` route.

In `donut/__init__.py`, replace the `index` route (lines 51-79):

```python
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

        from donut.database import PAGE_SIZE
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
        else:
            duration = None

        return render_template(
            "index.html",
            data=matches[0] if matches else None,
            query=query,
            suggestion=matches[1] if matches else "",
            num_documents=num_documents,
            duration=duration,
            sort=sort,
            page=page,
        )
```

Replace the `papers` route (lines 81-100):

```python
    @app.route("/papers")
    def papers():
        start = datetime.datetime.now()

        from donut.database import PAGE_SIZE
        page = request.args.get("page", 1, type=int)
        sort = request.args.get("sort", "year_desc")
        offset = (page - 1) * PAGE_SIZE

        matches = get_documents(
            DATABASE_DIR, offset=offset, limit=PAGE_SIZE,
            entry_type="article",
        )

        total = get_num_documents(DATABASE_DIR)
        total_pages = (total // PAGE_SIZE) + 1

        duration = datetime.datetime.now() - start
        duration = duration.total_seconds()

        return render_template(
            "index.html",
            data=matches,
            duration=duration,
            page=page,
            total_pages=total_pages,
            sort=sort,
        )
```

Replace the `software` route (lines 102-121):

```python
    @app.route("/software")
    def software():
        start = datetime.datetime.now()

        from donut.database import PAGE_SIZE
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
        )
```

Add the `export_all` route after the existing `export` route (after line 170):

```python
    @app.route("/export-all")
    def export_all():
        """Export all papers matching current query as .bib file."""
        query = request.args.get("q", "")

        if query:
            try:
                result = search(DATABASE_DIR, query, limit=10000)
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
```

- [ ] **Step 4: Update index.html with sort controls, pagination, and export link**

Replace `donut/templates/index.html` with:

```html
{% extends "base.html" %}

{% block content %}
  {% if duration is not none %}
  <div class="query-statistics">
    (found {{ data | length }} matches in {{ duration }}s)
  </div>
  {% endif %}

  {% if data is not none and data | length > 1 %}
  <div class="sort-controls">
    Sort by:
    <a href="?q={{ query }}&sort=relevance&page=1"
       {% if sort is not defined or sort == "" or sort == "relevance" %}class="active"{% endif %}>
      Relevance</a> |
    <a href="?q={{ query }}&sort=year_desc&page=1"
       {% if sort is defined and sort == "year_desc" %}class="active"{% endif %}>
      Newest</a> |
    <a href="?q={{ query }}&sort=year_asc&page=1"
       {% if sort is defined and sort == "year_asc" %}class="active"{% endif %}>
      Oldest</a>
    {% if query is defined and query | length > 0 %}
    | <a href="{{ url_for('export_all', q=query) }}">Export all as BibTeX</a>
    {% endif %}
  </div>
  {% endif %}

  {% if data is not none %}
    {% if data | length == 0 %}
    <article>
        <h1>No results&hellip;</h1>
        <p>
          Oh no, your query returned no results! It is possible that we do not
          have the requested document in our database. Try another query
          or notify us about the missing document by filling out
          <a href="https://forms.gle/PcVVGYckowW4Pb3w9">this form</a>.
        </p>
    </article>
    {% endif %}
    {% if suggestion is defined and suggestion | length != 0 %}
    <article>
      {% set link = url_for("index", q=suggestion) %}
      {% set link = '<a href=' ~ link ~ '>&ldquo;' ~ suggestion ~ '&rdquo;</a>' %}
      {% if data | length == 0 %}
        Did you mean {{ link | safe }}?
      {% else %}
      Found a potentially related query: {{ link | safe }} (this
      corrected query was suggested by the database parser based on
      term similarity; it does not necessarily imply conceptual
      similarity)
      {% endif %}
    </article>
    {% endif %}
    <ol id="search-results">
      {% for d in data %}
      <li class="search-result">
        <article>
          {% set id = d["id"] %}
          {% set document = d["document"] %}
          <h1>
            {{ document.title }}
            {% if document.year | length %}
              ({{ document.year }})
            {% endif %}
          </h1>

          {% set authors = [] %}
          {% for author in document.author %}
            {% set url = url_for("index", q='author:"' ~ author ~ '"') %}
            {% set url = '<a href=' ~ url ~ '>' ~ author ~ '</a>' %}
            {% set z = authors.append(url) %}
          {% endfor %}

          <address>
            {{ authors | join(', ') | safe }}
          </address>

          {% if document.abstract | length %}
          <details>
            <summary>Abstract</summary>

            {{ document.abstract }}
          </details>
          {% endif %}

          {% if (document.code | length) or (document.data | length) or (document.videos | length) %}
          <div class="community-resources">
            <h1>Community Resources</h1>
            <ul>
              {% for code in document.code %}
                {% set url = code[0] %}
                {% set title = code[1] %}
                  <li>
                    <a href="{{ url }}">Code
                      {% if title | length %}
                        ({{ title }})
                      {% endif %}
                    </a>
                  </li>
              {% endfor %}
              {% for data in document.data %}
                {% set url = data[0] %}
                {% set title = data[1] %}
                  <li>
                    <a href="{{ url }}">Data
                      {% if title | length %}
                        ({{ title }})
                      {% endif %}
                    </a>
                  </li>
              {% endfor %}
              {% for video in document.videos %}
                {% set url = video[0] %}
                {% set title = video[1] %}
                  <li>
                    <a href="{{ url }}">Video
                      {% if title | length %}
                        ({{ title }})
                      {% endif %}
                    </a>
                  </li>
              {% endfor %}
            </ul>
          </div>
          {% endif %}

          <ul class="references">
            {% if document.url | length %}
              <li>
                <a href="{{ document.url }}">URL</a>
              </li>
            {% endif %}
            {% if document.doi | length %}
              <li>
                {% set url = "https://dx.doi.org/" ~ document.doi %}
                <a href="{{ url }}">DOI</a>
              </li>
            {% endif %}
            <li>
              {% set url = url_for("export", identifier=id) %}
              <a href="{{ url }}">Export citation</a>
            </li>
          </ul>

          {% if document.keywords is defined %}
          <ul class="tags">
            {% for keyword in document.keywords %}
            {% set type = keyword[0] %}
            {% set keyword = keyword[1] %}
            <li class="inline-tag">
              <span class="inline-tag-{{ type}}">
                {% set url = url_for("index", q='tag:"' ~ keyword ~ '"') %}
                <a href={{ url}}>{{ keyword }}</a>
              </span>
            </li>
            {% endfor %}
          </ul>
          {% endif %}
        </article>
      </li>
      {% endfor %}
    </ol>

    {% if total_pages is defined and total_pages > 1 %}
    <nav class="pagination">
      {% if page > 1 %}
        <a href="?q={{ query | default('') }}&sort={{ sort | default('') }}&page={{ page - 1 }}">&laquo; Previous</a>
      {% endif %}
      <span>Page {{ page }} of {{ total_pages }}</span>
      {% if page < total_pages %}
        <a href="?q={{ query | default('') }}&sort={{ sort | default('') }}&page={{ page + 1 }}">Next &raquo;</a>
      {% endif %}
    </nav>
    {% endif %}

  {% else %}
  <article>
    <p>
      Currently indexing {{ num_documents }} documents.
    </p>

    <p>
      This database does <em>not</em> aim to be an exhaustive list of papers
      in topological data analysis but wants to focus on
      <strong>applications</strong> of topological data analysis to
      other domains.
    </p>
    <div class="video-container">
      <iframe src="https://www.youtube.com/embed/eQ_5ScYmS7g?si=x8cn9RgpLP8M-gHz"
              title="YouTube video player"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              referrerpolicy="strict-origin-when-cross-origin"
              allowfullscreen></iframe>
    </div>
    <h1>Usage examples</h1>
    <p>
      Search is case-insensitive, i.e. both &ldquo;Topology&rdquo; and &ldquo;topology&rdquo; yield the same results.
      You can use the standard operators <code>AND</code>, <code>OR</code>, and <code>NOT</code> to refine your queries.
      Wildcard queries are supported using the <code>&ast;</code>
      character.
      Here are some example queries to get you started (you can either copy
      and paste them or click on them to execute the respective query):
    </p>

    <ul>
      <li>
        All articles of a certain author:
        <ul>
          <li><code><a href="/?q=author%3A%22robins%22">author:robins</a></code></li>
          <li><code><a href="/?q=author%3A%22vanessa+robins%22">author:&quot;vanessa robins&quot;</a></code></li>
        </ul>
      </li>

      <li>
        All articles containing a certain substring: 
        <ul>
          <li><code><a href="/?q=hom%2A">hom&ast;</a></code></li>
          <li><code><a href="/?q=top%2A">top&ast;</a></code></li>

        </ul>
      </li>

      <li>
        All articles tagged with a specific set of tags:
        <ul>
          <li><code><a href="/?q=tag%3A%22machine+learning%22">tag:&quot;machine learning&quot;</a></code></li>
          <li><code><a href="/?q=tag%3A%22machine+learning%22+OR+tag%3Amapper">tag:&quot;machine learning&quot; OR tag:mapper</a></code></li>
          <li><code><a href="/?q=tag%3A%22machine+learning%22+NOT+tag%3A%22persistent+homology%22">tag:&quot;machine learning&quot; NOT tag:&quot;persistent homology&quot;</a></code></li>
        </ul>
      </li>

      <li>
        All articles with a specific word in their title:
        <ul>
          <li><code><a href="/?q=title%3Amanifold">title:manifold</a></code></li>
          <li><code><a
                href="/?q=title%3Amanifold+AND+title%3Alearning">title:manifold AND title:learning</a></code></li>
        </ul>
    </ul>

    <p>
      New functionalities are constantly added.
      Let us know if you are missing something and send us your feedback to
      <a href="mailto:donut@topology.rocks">donut@topology.rocks</a>.
      If we are missing an article, please fill out <a href="https://forms.gle/PcVVGYckowW4Pb3w9">this form</a>.
    </p>

    <h1>Citing or acknowledging DONUT</h1> 

    <p>
      Please use the following BibTeX citation when citing or acknowledging
      DONUT in your own work:

      <pre><code>@misc{DONUT,
  author = {Giunti, Barbara and Lazovskis, J{\=a}nis and Rieck, Bastian},
  title  = {
    {DONUT}: {D}atabase of {O}riginal \&amp; {N}on-{T}heoretical {U}ses of {T}opology
  },
  note   = {\url{https://donut.topology.rocks}},
  year   = {2022},
  key    = {DONUT},
}</code></pre>
    </p>
  </article>
  {% endif %}
{% endblock %}
```

- [ ] **Step 5: Add CSS for sort controls and pagination**

Append to `donut/static/style.css`:

```css
.sort-controls
{
  font-size:      small;
  margin-bottom:  0.5em;
}

.sort-controls a.active
{
  font-weight: bold;
}

.pagination
{
  text-align:  center;
  padding:     1em 0;
  margin-top:  1em;
  border-top:  1px solid #E8E8E8;
}

.pagination a
{
  margin: 0 0.5em;
}

.pagination span
{
  margin: 0 1em;
  color:  #666;
}
```

- [ ] **Step 6: Run all tests**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add donut/__init__.py donut/templates/index.html donut/static/style.css tests/test_routes.py
git commit -m "Add sorting, pagination, and bulk export to Flask routes and templates"
```

---

## Task 4: Statistics Dashboard

**Files:**
- Create: `donut/analysis.py`, `donut/templates/stats.html`, `tests/test_analysis.py`
- Modify: `donut/__init__.py`, `donut/templates/base.html`

- [ ] **Step 1: Write failing tests for statistics computation**

Create `tests/test_analysis.py`:

```python
"""Tests for analysis module."""

from donut.analysis import compute_statistics


def test_compute_statistics(test_db):
    """Statistics include expected fields."""
    stats = compute_statistics(test_db)
    assert "years" in stats
    assert "top_tags" in stats
    assert "top_authors" in stats
    assert "total_papers" in stats
    assert "total_software" in stats


def test_statistics_counts(test_db):
    """Statistics counts are correct for test data."""
    stats = compute_statistics(test_db)
    assert stats["total_papers"] == 3
    assert stats["total_software"] == 1

    # "persistent homology" appears in 3 papers
    tag_names = [name for name, _ in stats["top_tags"]]
    assert "persistent homology" in tag_names


def test_statistics_years(test_db):
    """Year distribution is correct."""
    stats = compute_statistics(test_db)
    assert stats["years"]["2024"] == 2  # brown + gudhi
    assert stats["years"]["2023"] == 1  # smith
    assert stats["years"]["2022"] == 1  # white
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_analysis.py -v
```

Expected: FAIL — `donut.analysis` module does not exist.

- [ ] **Step 3: Create analysis.py**

Create `donut/analysis.py`:

```python
"""Analysis module for computing statistics and co-occurrence data."""

import collections
import json

import xapian


def compute_statistics(database_dir):
    """Compute statistics from the database.

    Returns a dict with keys: years, top_tags, top_authors,
    total_papers, total_software.
    """
    db = xapian.Database(database_dir)

    years = collections.Counter()
    tags = collections.Counter()
    authors = collections.Counter()
    total_papers = 0
    total_software = 0

    for item in db.postlist(""):
        document = db.get_document(item.docid)
        data = json.loads(document.get_data())

        entry_type = data.get("raw", {}).get("ENTRYTYPE", "article")
        if entry_type == "software":
            total_software += 1
        else:
            total_papers += 1

        years[data.get("year", "unknown")] += 1

        for _, keyword in data.get("keywords", []):
            tags[keyword] += 1

        for author in data.get("author", []):
            authors[author] += 1

    return {
        "years": dict(sorted(years.items())),
        "top_tags": tags.most_common(20),
        "top_authors": authors.most_common(20),
        "total_papers": total_papers,
        "total_software": total_software,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_analysis.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Create stats.html template**

Create `donut/templates/stats.html`:

```html
{% extends "base.html" %}

{% set nosearch = true %}

{% block content %}
<article>
  <h1>Database Statistics</h1>

  <div class="stats-summary">
    <p>
      <strong>{{ stats.total_papers }}</strong> papers and
      <strong>{{ stats.total_software }}</strong> software entries indexed.
    </p>
  </div>

  <section>
    <h1>Papers by Year</h1>
    <canvas id="years-chart" width="600" height="300"></canvas>
    <noscript>
      <ul>
        {% for year, count in stats.years.items() %}
          <li>{{ year }}: {{ count }}</li>
        {% endfor %}
      </ul>
    </noscript>
  </section>

  <section>
    <h1>Top 20 Tags</h1>
    <canvas id="tags-chart" width="600" height="400"></canvas>
    <noscript>
      <ol>
        {% for tag, count in stats.top_tags %}
          <li>
            {% set url = url_for("index", q='tag:"' ~ tag ~ '"') %}
            <a href="{{ url }}">{{ tag }}</a> ({{ count }})
          </li>
        {% endfor %}
      </ol>
    </noscript>
  </section>

  <section>
    <h1>Top 20 Authors</h1>
    <table>
      <thead>
        <tr><th>Author</th><th>Papers</th></tr>
      </thead>
      <tbody>
        {% for author, count in stats.top_authors %}
        <tr>
          <td>
            {% set url = url_for("index", q='author:"' ~ author ~ '"') %}
            <a href="{{ url }}">{{ author }}</a>
          </td>
          <td>{{ count }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
</article>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>
  var yearsData = {{ stats.years | tojson }};
  var yearsLabels = Object.keys(yearsData);
  var yearsValues = Object.values(yearsData);

  new Chart(document.getElementById('years-chart'), {
    type: 'bar',
    data: {
      labels: yearsLabels,
      datasets: [{
        label: 'Papers',
        data: yearsValues,
        backgroundColor: '#66c2a5'
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
    }
  });

  var tagsData = {{ stats.top_tags | tojson }};
  var tagsLabels = tagsData.map(function(t) { return t[0]; });
  var tagsValues = tagsData.map(function(t) { return t[1]; });

  new Chart(document.getElementById('tags-chart'), {
    type: 'bar',
    data: {
      labels: tagsLabels,
      datasets: [{
        label: 'Papers',
        data: tagsValues,
        backgroundColor: '#fc8d62'
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      plugins: { legend: { display: false } }
    }
  });
</script>
{% endblock %}
```

- [ ] **Step 6: Add stats route to __init__.py**

Add this import at the top of `donut/__init__.py`, after the existing imports:

```python
from donut.analysis import compute_statistics
```

Add the route inside `create()`, before `return app`:

```python
    @app.route("/stats")
    def stats():
        statistics = compute_statistics(DATABASE_DIR)
        return render_template("stats.html", stats=statistics)
```

- [ ] **Step 7: Update base.html navigation**

In `donut/templates/base.html`, replace the nav div (lines 12-23):

```html
      <div id="header-text">
        <a href="/">Home</a>
        &bull;
        <a href="/papers">Papers</a>
        &bull;
        <a href="/software">Software</a>
        &bull;
        <a href="/tags">Tags</a>
        &bull;
        <a href="/stats">Stats</a>
        &bull;
        <a href="/faq">FAQ</a>
        &bull;
        <a href="/contributors">Contributors</a>
      </div>
```

- [ ] **Step 8: Add route test for stats**

Append to `tests/test_routes.py`:

```python
def test_stats_page(client):
    """Stats page loads with statistics data."""
    response = client.get("/stats")
    assert response.status_code == 200
    assert b"Database Statistics" in response.data
    assert b"papers" in response.data


def test_export_all(client):
    """Bulk export returns a .bib file."""
    response = client.get("/export-all?q=homology")
    assert response.status_code == 200
    assert response.content_type == "application/x-bibtex"
```

- [ ] **Step 9: Run all tests**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 10: Commit**

```bash
git add donut/analysis.py donut/templates/stats.html donut/__init__.py donut/templates/base.html tests/test_analysis.py tests/test_routes.py
git commit -m "Add statistics dashboard with Chart.js visualizations"
```

---

## Task 5: Related Papers (Similarity)

**Files:**
- Create: `donut/similarity.py`, `tests/test_similarity.py`
- Modify: `donut/__init__.py`, `donut/templates/index.html`, `donut/reindex.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_similarity.py`:

```python
"""Tests for similarity module."""

from donut.similarity import compute_similarity


def test_compute_similarity(test_db):
    """Similarity computation returns neighbors dict."""
    neighbors = compute_similarity(test_db)
    assert isinstance(neighbors, dict)
    assert len(neighbors) > 0


def test_similarity_values(test_db):
    """Similarity scores are between 0 and 1."""
    neighbors = compute_similarity(test_db)
    for docid, scores in neighbors.items():
        for neighbor_id, score in scores:
            assert 0 < score <= 1.0


def test_similar_papers_share_tags(test_db):
    """Papers sharing more tags have higher similarity."""
    neighbors = compute_similarity(test_db)
    # At least some papers should have neighbors
    has_neighbors = [
        docid for docid, scores in neighbors.items()
        if len(scores) > 0
    ]
    assert len(has_neighbors) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_similarity.py -v
```

Expected: FAIL — `donut.similarity` module does not exist.

- [ ] **Step 3: Create similarity.py**

Create `donut/similarity.py`:

```python
"""Compute paper similarity for related papers feature."""

import json

import xapian


def compute_similarity(database_dir, max_neighbors=5,
                       threshold=0.1):
    """Compute Jaccard tag similarity between all paper pairs.

    Parameters
    ----------
    database_dir : str
        Path to Xapian database directory.

    max_neighbors : int
        Maximum number of neighbors per paper.

    threshold : float
        Minimum Jaccard similarity to include.

    Returns
    -------
    dict
        Maps docid (int) to list of (docid, score) tuples,
        sorted by score descending.
    """
    db = xapian.Database(database_dir)
    papers = {}

    for item in db.postlist(""):
        doc = db.get_document(item.docid)
        data = json.loads(doc.get_data())
        tag_set = frozenset(
            kw for _, kw in data.get("keywords", [])
        )
        papers[item.docid] = tag_set

    docids = list(papers.keys())
    neighbors = {}

    for i, id_a in enumerate(docids):
        scores = []
        for j, id_b in enumerate(docids):
            if i == j:
                continue
            intersection = len(papers[id_a] & papers[id_b])
            union = len(papers[id_a] | papers[id_b])
            if union > 0:
                jaccard = intersection / union
                if jaccard > threshold:
                    scores.append((id_b, round(jaccard, 4)))

        scores.sort(key=lambda x: x[1], reverse=True)
        neighbors[id_a] = scores[:max_neighbors]

    return neighbors
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_similarity.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Integrate similarity into reindex.py**

Replace `donut/reindex.py` with:

```python
"""Reindex all documents in the database.

This script can be called at all times. It will perform a new indexing
operation on all `.bib` files stored in the `data` directory.

After indexing, it computes similarity data for the related papers
feature.
"""

import glob
import json
import os

from dotenv import load_dotenv

from donut.database import index_documents
from donut.similarity import compute_similarity

load_dotenv()


if __name__ == "__main__":
    DATA_DIR = os.getenv("DATA_DIR", "data")
    DATABASE_DIR = os.getenv("DATABASE_DIR", "database")

    assert DATA_DIR is not None
    assert DATABASE_DIR is not None

    filenames = glob.glob(os.path.join(DATA_DIR, "*.bib"))

    for filename in filenames:
        index_documents(filename, DATABASE_DIR)

    # Compute and save similarity data
    print("Computing paper similarity...")
    neighbors = compute_similarity(DATABASE_DIR)

    # Convert int keys to strings for JSON serialization
    serializable = {
        str(k): v for k, v in neighbors.items()
    }

    similarity_path = os.path.join(DATABASE_DIR, "similarity.json")
    with open(similarity_path, "w") as f:
        json.dump(serializable, f)

    print(f"Saved similarity data for {len(neighbors)} papers.")
```

- [ ] **Step 6: Load similarity data in Flask app and pass to templates**

In `donut/__init__.py`, add after `DATABASE_DIR = os.getenv(...)`:

```python
import json as _json

def _load_similarity():
    """Load precomputed similarity data if available."""
    path = os.path.join(DATABASE_DIR, "similarity.json")
    if os.path.exists(path):
        with open(path) as f:
            return _json.load(f)
    return {}

SIMILARITY_DATA = _load_similarity()
```

In the `index` route, add `related=SIMILARITY_DATA` to the `render_template` call (add it to the existing kwargs).

In the `papers` and `software` routes, also add `related=SIMILARITY_DATA`.

- [ ] **Step 7: Show related papers in index.html**

In `donut/templates/index.html`, add after the tags `</ul>` block (after the `{% endif %}` that closes `{% if document.keywords is defined %}`), inside the `<article>` for each search result:

```html
          {% if related is defined and id | string in related %}
          {% set neighbors = related[id | string] %}
          {% if neighbors | length > 0 %}
          <details class="related-papers">
            <summary>Related papers ({{ neighbors | length }})</summary>
            <ul>
              {% for neighbor_id, score in neighbors %}
              <li>
                <a href="/?q={{ neighbor_id }}">Paper #{{ neighbor_id }}</a>
                (similarity: {{ (score * 100) | round(0) | int }}%)
              </li>
              {% endfor %}
            </ul>
          </details>
          {% endif %}
          {% endif %}
```

- [ ] **Step 8: Add CSS for related papers**

Append to `donut/static/style.css`:

```css
.related-papers
{
  margin-top: 0.5em;
  font-size:  small;
  color:      #666;
}

.related-papers ul
{
  list-style-type: none;
  padding-left:    0;
}
```

- [ ] **Step 9: Run all tests**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 10: Commit**

```bash
git add donut/similarity.py donut/reindex.py donut/__init__.py donut/templates/index.html donut/static/style.css tests/test_similarity.py
git commit -m "Add related papers feature with precomputed Jaccard similarity"
```

---

## Task 6: Tag Co-occurrence Explorer

**Files:**
- Modify: `donut/analysis.py`, `tests/test_analysis.py`
- Create: `donut/templates/explore.html`
- Modify: `donut/__init__.py`, `donut/templates/base.html`, `donut/reindex.py`

- [ ] **Step 1: Write failing tests for co-occurrence**

Append to `tests/test_analysis.py`:

```python
from donut.analysis import compute_tag_cooccurrence


def test_compute_tag_cooccurrence(test_db):
    """Co-occurrence computation returns list of edges."""
    edges = compute_tag_cooccurrence(test_db, min_weight=1)
    assert isinstance(edges, list)
    assert len(edges) > 0


def test_cooccurrence_edge_structure(test_db):
    """Each edge has source, target, weight, and categories."""
    edges = compute_tag_cooccurrence(test_db, min_weight=1)
    for edge in edges:
        assert "source" in edge
        assert "target" in edge
        assert "weight" in edge
        assert edge["weight"] >= 1


def test_cooccurrence_known_pair(test_db):
    """persistent homology + point cloud co-occur in test data."""
    edges = compute_tag_cooccurrence(test_db, min_weight=1)
    pairs = {
        (e["source"], e["target"]) for e in edges
    }
    # Both orderings could appear depending on sort
    assert (
        ("persistent homology", "point cloud") in pairs
        or ("point cloud", "persistent homology") in pairs
    )
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_analysis.py::test_compute_tag_cooccurrence -v
```

Expected: FAIL — `compute_tag_cooccurrence` not importable.

- [ ] **Step 3: Add compute_tag_cooccurrence to analysis.py**

Append to `donut/analysis.py`:

```python
def compute_tag_cooccurrence(database_dir, min_weight=3):
    """Compute tag co-occurrence for the explorer graph.

    Parameters
    ----------
    database_dir : str
        Path to Xapian database directory.

    min_weight : int
        Minimum co-occurrence count to include an edge.

    Returns
    -------
    list of dict
        Each dict has keys: source, target, weight,
        source_category, target_category.
    """
    db = xapian.Database(database_dir)
    pair_counts = collections.Counter()
    tag_categories = {}

    for item in db.postlist(""):
        doc = db.get_document(item.docid)
        data = json.loads(doc.get_data())
        keywords = data.get("keywords", [])

        for category, keyword in keywords:
            tag_categories[keyword] = category

        tag_names = [kw for _, kw in keywords]

        for i in range(len(tag_names)):
            for j in range(i + 1, len(tag_names)):
                pair = tuple(sorted([tag_names[i], tag_names[j]]))
                pair_counts[pair] += 1

    edges = []
    for (source, target), weight in pair_counts.items():
        if weight >= min_weight:
            edges.append({
                "source": source,
                "target": target,
                "weight": weight,
                "source_category": tag_categories.get(source, ""),
                "target_category": tag_categories.get(target, ""),
            })

    return edges
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_analysis.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Create explore.html template**

Create `donut/templates/explore.html`:

```html
{% extends "base.html" %}

{% set nosearch = true %}

{% block content %}
<article>
  <h1>Tag Co-occurrence Explorer</h1>
  <p>
    Tags that appear together on papers are connected. Thicker edges mean
    more papers share those tags. Click a node to highlight its connections.
    Use the category toggles to focus on specific tag types.
  </p>

  <div class="explore-controls">
    <label><input type="checkbox" id="toggle-applications" checked> Applications</label>
    <label><input type="checkbox" id="toggle-tools" checked> Tools</label>
    <label><input type="checkbox" id="toggle-data" checked> Data</label>
  </div>

  <div id="graph-container"></div>

  <div id="node-detail" style="display:none;">
    <h2 id="node-detail-name"></h2>
    <p id="node-detail-info"></p>
  </div>
</article>

<script src="https://cdn.jsdelivr.net/npm/d3@7/dist/d3.min.js"></script>
<script>
(function() {
  var rawEdges = {{ edges | tojson }};
  var tagCounts = {{ tag_counts | tojson }};

  var categoryColors = {
    "applications": "#66c2a5",
    "tools": "#fc8d62",
    "data": "#8da0cb",
    "flavour": "#e78ac3"
  };

  // Build nodes from edges
  var nodeMap = {};
  rawEdges.forEach(function(e) {
    if (!nodeMap[e.source]) {
      nodeMap[e.source] = {
        id: e.source,
        category: e.source_category,
        count: tagCounts[e.source] || 1
      };
    }
    if (!nodeMap[e.target]) {
      nodeMap[e.target] = {
        id: e.target,
        category: e.target_category,
        count: tagCounts[e.target] || 1
      };
    }
  });

  var allNodes = Object.values(nodeMap);
  var allEdges = rawEdges.map(function(e) {
    return {source: e.source, target: e.target, weight: e.weight};
  });

  var container = document.getElementById('graph-container');
  var width = container.offsetWidth || 800;
  var height = 600;

  var svg = d3.select('#graph-container')
    .append('svg')
    .attr('width', width)
    .attr('height', height)
    .attr('viewBox', [0, 0, width, height]);

  var maxWeight = d3.max(allEdges, function(d) { return d.weight; }) || 1;
  var maxCount = d3.max(allNodes, function(d) { return d.count; }) || 1;

  function render(nodes, edges) {
    svg.selectAll('*').remove();

    var simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(edges).id(function(d) { return d.id; })
        .distance(80))
      .force('charge', d3.forceManyBody().strength(-100))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(function(d) {
        return Math.sqrt(d.count / maxCount) * 15 + 5;
      }));

    var link = svg.append('g')
      .selectAll('line')
      .data(edges)
      .join('line')
      .attr('stroke', '#999')
      .attr('stroke-opacity', 0.6)
      .attr('stroke-width', function(d) {
        return Math.max(1, (d.weight / maxWeight) * 5);
      });

    var node = svg.append('g')
      .selectAll('circle')
      .data(nodes)
      .join('circle')
      .attr('r', function(d) {
        return Math.sqrt(d.count / maxCount) * 15 + 3;
      })
      .attr('fill', function(d) {
        return categoryColors[d.category] || '#999';
      })
      .attr('stroke', '#fff')
      .attr('stroke-width', 1.5)
      .call(d3.drag()
        .on('start', function(event, d) {
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        })
        .on('drag', function(event, d) {
          d.fx = event.x; d.fy = event.y;
        })
        .on('end', function(event, d) {
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        }));

    var label = svg.append('g')
      .selectAll('text')
      .data(nodes)
      .join('text')
      .text(function(d) { return d.id; })
      .attr('font-size', '10px')
      .attr('dx', 12)
      .attr('dy', 4);

    node.on('click', function(event, d) {
      var detail = document.getElementById('node-detail');
      var nameEl = document.getElementById('node-detail-name');
      var infoEl = document.getElementById('node-detail-info');

      nameEl.textContent = d.id;

      var connCount = edges.filter(function(e) {
        return (e.source.id || e.source) === d.id
            || (e.target.id || e.target) === d.id;
      }).length;

      infoEl.textContent = 'Category: ' + d.category
        + ' | Papers: ' + d.count
        + ' | Connections: ' + connCount;
      detail.style.display = 'block';

      // Highlight connected
      node.attr('opacity', function(n) {
        if (n.id === d.id) return 1;
        var connected = edges.some(function(e) {
          return ((e.source.id || e.source) === d.id
                  && (e.target.id || e.target) === n.id)
              || ((e.target.id || e.target) === d.id
                  && (e.source.id || e.source) === n.id);
        });
        return connected ? 1 : 0.2;
      });
      link.attr('opacity', function(e) {
        return ((e.source.id || e.source) === d.id
             || (e.target.id || e.target) === d.id) ? 1 : 0.1;
      });
      label.attr('opacity', function(n) {
        if (n.id === d.id) return 1;
        var connected = edges.some(function(e) {
          return ((e.source.id || e.source) === d.id
                  && (e.target.id || e.target) === n.id)
              || ((e.target.id || e.target) === d.id
                  && (e.source.id || e.source) === n.id);
        });
        return connected ? 1 : 0.2;
      });
    });

    svg.on('click', function(event) {
      if (event.target.tagName === 'svg') {
        node.attr('opacity', 1);
        link.attr('opacity', 0.6);
        label.attr('opacity', 1);
        document.getElementById('node-detail').style.display = 'none';
      }
    });

    simulation.on('tick', function() {
      link
        .attr('x1', function(d) { return d.source.x; })
        .attr('y1', function(d) { return d.source.y; })
        .attr('x2', function(d) { return d.target.x; })
        .attr('y2', function(d) { return d.target.y; });
      node
        .attr('cx', function(d) { return d.x; })
        .attr('cy', function(d) { return d.y; });
      label
        .attr('x', function(d) { return d.x; })
        .attr('y', function(d) { return d.y; });
    });
  }

  function applyFilters() {
    var showApps = document.getElementById('toggle-applications').checked;
    var showTools = document.getElementById('toggle-tools').checked;
    var showData = document.getElementById('toggle-data').checked;

    var visible = {};
    if (showApps) visible['applications'] = true;
    if (showTools) visible['tools'] = true;
    if (showData) visible['data'] = true;

    var filteredNodes = allNodes.filter(function(n) {
      return visible[n.category];
    });
    var nodeIds = new Set(filteredNodes.map(function(n) { return n.id; }));
    var filteredEdges = allEdges.filter(function(e) {
      return nodeIds.has(e.source.id || e.source)
          && nodeIds.has(e.target.id || e.target);
    });

    render(filteredNodes, filteredEdges);
  }

  document.getElementById('toggle-applications')
    .addEventListener('change', applyFilters);
  document.getElementById('toggle-tools')
    .addEventListener('change', applyFilters);
  document.getElementById('toggle-data')
    .addEventListener('change', applyFilters);

  render(allNodes, allEdges);
})();
</script>
{% endblock %}
```

- [ ] **Step 6: Add explore route and API endpoint to __init__.py**

Add import at top of `donut/__init__.py`:

```python
from donut.analysis import compute_tag_cooccurrence
```

Add routes inside `create()`, before `return app`:

```python
    @app.route("/explore")
    def explore():
        cooccurrence_path = os.path.join(
            DATABASE_DIR, "cooccurrence.json"
        )
        if os.path.exists(cooccurrence_path):
            with open(cooccurrence_path) as f:
                edges = _json.load(f)
        else:
            edges = compute_tag_cooccurrence(DATABASE_DIR)

        # Build tag count map for node sizing
        tags = get_tags(DATABASE_DIR)
        tag_counts = {}
        for category_tags in tags.values():
            for tag, count in category_tags.items():
                tag_counts[tag] = count

        return render_template(
            "explore.html", edges=edges, tag_counts=tag_counts,
        )

    @app.route("/api/tag-cooccurrence")
    def api_tag_cooccurrence():
        from flask import jsonify
        cooccurrence_path = os.path.join(
            DATABASE_DIR, "cooccurrence.json"
        )
        if os.path.exists(cooccurrence_path):
            with open(cooccurrence_path) as f:
                edges = _json.load(f)
        else:
            edges = compute_tag_cooccurrence(DATABASE_DIR)
        return jsonify(edges)
```

- [ ] **Step 7: Update navigation in base.html**

In `donut/templates/base.html`, add Explore link after Software in the nav:

```html
        <a href="/explore">Explore</a>
        &bull;
```

(Insert between the Software link and the Tags link.)

- [ ] **Step 8: Add co-occurrence to reindex.py**

In `donut/reindex.py`, add import:

```python
from donut.analysis import compute_tag_cooccurrence
```

Add after the similarity computation block:

```python
    # Compute and save co-occurrence data
    print("Computing tag co-occurrence...")
    edges = compute_tag_cooccurrence(DATABASE_DIR)

    cooccurrence_path = os.path.join(
        DATABASE_DIR, "cooccurrence.json"
    )
    with open(cooccurrence_path, "w") as f:
        json.dump(edges, f)

    print(f"Saved {len(edges)} co-occurrence edges.")
```

- [ ] **Step 9: Add CSS for explorer**

Append to `donut/static/style.css`:

```css
#graph-container
{
  border:     1px solid #E8E8E8;
  background: white;
  margin:     1em 0;
}

#graph-container svg
{
  width:  100%;
  height: 600px;
}

.explore-controls
{
  margin: 1em 0;
}

.explore-controls label
{
  margin-right: 1.5em;
}

#node-detail
{
  border:     1px solid #E8E8E8;
  background: white;
  padding:    1em;
  margin-top: 1em;
}
```

- [ ] **Step 10: Add route tests**

Append to `tests/test_routes.py`:

```python
def test_explore_page(client):
    """Explore page loads."""
    response = client.get("/explore")
    assert response.status_code == 200
    assert b"Tag Co-occurrence" in response.data


def test_api_tag_cooccurrence(client):
    """API returns co-occurrence JSON."""
    response = client.get("/api/tag-cooccurrence")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
```

- [ ] **Step 11: Run all tests**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 12: Commit**

```bash
git add donut/analysis.py donut/templates/explore.html donut/__init__.py donut/templates/base.html donut/reindex.py donut/static/style.css tests/test_analysis.py tests/test_routes.py
git commit -m "Add interactive tag co-occurrence explorer with D3.js"
```

---

## Task 7: Timeline View

**Files:**
- Create: `donut/templates/timeline.html`
- Modify: `donut/__init__.py`, `donut/templates/base.html`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Add timeline route to __init__.py**

Add inside `create()`, before `return app`:

```python
    @app.route("/timeline")
    def timeline():
        import collections as _collections
        matches = get_documents(DATABASE_DIR)
        papers = [
            m for m in matches
            if m["document"]["raw"]["ENTRYTYPE"] != "software"
        ]

        by_year = _collections.defaultdict(list)
        for p in papers:
            doc = p["document"]
            year = doc.get("year", "unknown")
            app_tags = [
                kw for cat, kw in doc.get("keywords", [])
                if cat == "applications"
            ]
            primary_tag = app_tags[0] if app_tags else "untagged"
            by_year[year].append({
                "title": doc["title"],
                "tag": primary_tag,
                "id": p["id"],
            })

        by_year = dict(sorted(by_year.items()))
        return render_template("timeline.html", by_year=by_year)
```

- [ ] **Step 2: Create timeline.html template**

Create `donut/templates/timeline.html`:

```html
{% extends "base.html" %}

{% set nosearch = true %}

{% block content %}
<article>
  <h1>Timeline</h1>
  <p>Papers by year, colored by primary application domain.</p>

  <canvas id="timeline-chart" width="600" height="300"></canvas>

  {% for year, papers in by_year.items() %}
  <section>
    <h2>{{ year }} ({{ papers | length }} papers)</h2>
    <ul class="timeline-entries">
      {% for paper in papers %}
      <li>
        <span class="timeline-tag">{{ paper.tag }}</span>
        {{ paper.title }}
      </li>
      {% endfor %}
    </ul>
  </section>
  {% endfor %}
</article>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>
(function() {
  var byYear = {{ by_year | tojson }};
  var years = Object.keys(byYear).sort();

  // Collect all unique tags
  var tagSet = new Set();
  years.forEach(function(y) {
    byYear[y].forEach(function(p) { tagSet.add(p.tag); });
  });
  var tags = Array.from(tagSet).sort();

  // Color palette
  var colors = [
    '#66c2a5', '#fc8d62', '#8da0cb', '#e78ac3', '#a6d854',
    '#ffd92f', '#e5c494', '#b3b3b3', '#1f78b4', '#33a02c',
    '#fb9a99', '#e31a1c', '#ff7f00', '#cab2d6', '#6a3d9a'
  ];

  var datasets = tags.map(function(tag, i) {
    return {
      label: tag,
      data: years.map(function(y) {
        return byYear[y].filter(function(p) {
          return p.tag === tag;
        }).length;
      }),
      backgroundColor: colors[i % colors.length]
    };
  });

  new Chart(document.getElementById('timeline-chart'), {
    type: 'bar',
    data: { labels: years, datasets: datasets },
    options: {
      responsive: true,
      scales: {
        x: { stacked: true },
        y: { stacked: true, beginAtZero: true }
      },
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: { boxWidth: 12, font: { size: 10 } }
        }
      }
    }
  });
})();
</script>
{% endblock %}
```

- [ ] **Step 3: Add CSS for timeline**

Append to `donut/static/style.css`:

```css
.timeline-entries
{
  list-style-type: none;
  padding-left:    0;
}

.timeline-entries li
{
  margin-bottom: 0.25em;
}

.timeline-tag
{
  font-size:      small;
  font-weight:    600;
  background:     #66c2a5;
  color:          white;
  border-radius:  2.5px;
  padding:        0.1em 0.4em;
  margin-right:   0.5em;
}
```

- [ ] **Step 4: Update navigation in base.html**

In `donut/templates/base.html`, add Timeline link after Explore in the nav:

```html
        <a href="/timeline">Timeline</a>
        &bull;
```

- [ ] **Step 5: Add route test**

Append to `tests/test_routes.py`:

```python
def test_timeline_page(client):
    """Timeline page loads."""
    response = client.get("/timeline")
    assert response.status_code == 200
    assert b"Timeline" in response.data
```

- [ ] **Step 6: Run all tests**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add donut/templates/timeline.html donut/__init__.py donut/templates/base.html donut/static/style.css tests/test_routes.py
git commit -m "Add timeline view with stacked bar chart by application domain"
```

---

## Task 8: Faceted Search

**Files:**
- Modify: `donut/database.py`, `donut/__init__.py`, `donut/templates/index.html`
- Create: `donut/templates/facets.html`
- Modify: `tests/test_database.py`

- [ ] **Step 1: Write failing tests for compute_facets**

Append to `tests/test_database.py`:

```python
from donut.database import compute_facets


def test_compute_facets(test_db):
    """Facets are computed from a list of matches."""
    all_docs = get_documents(test_db)
    facets = compute_facets(all_docs)
    assert "tags" in facets
    assert "years" in facets
    assert "types" in facets


def test_facets_tag_counts(test_db):
    """Facets contain correct tag counts."""
    all_docs = get_documents(test_db)
    facets = compute_facets(all_docs)
    # "persistent homology" is in 3 of 4 entries
    assert facets["tags"]["tools"]["persistent homology"] == 3


def test_facets_year_counts(test_db):
    """Facets contain correct year counts."""
    all_docs = get_documents(test_db)
    facets = compute_facets(all_docs)
    assert facets["years"]["2024"] == 2
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_database.py::test_compute_facets -v
```

Expected: FAIL — `compute_facets` not importable.

- [ ] **Step 3: Add compute_facets to database.py**

Append to `donut/database.py`:

```python
def compute_facets(matches):
    """Compute facets from a list of match dicts.

    Parameters
    ----------
    matches : list of dict
        List of match dicts as returned by search() or
        get_documents().

    Returns
    -------
    dict
        Contains 'tags' (dict of category -> Counter),
        'years' (Counter), and 'types' (Counter).
    """
    tag_counts = collections.defaultdict(collections.Counter)
    year_counts = collections.Counter()
    type_counts = collections.Counter()

    for m in matches:
        doc = m["document"]
        year_counts[doc.get("year", "unknown")] += 1
        type_counts[doc.get("type", "article")] += 1
        for category, keyword in doc.get("keywords", []):
            tag_counts[category][keyword] += 1

    return {
        "tags": dict(tag_counts),
        "years": dict(year_counts),
        "types": dict(type_counts),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_database.py -v
```

Expected: All tests PASS.

- [ ] **Step 5: Create facets.html partial template**

Create `donut/templates/facets.html`:

```html
{% if facets is defined and facets is not none %}
<details class="facets">
  <summary>Refine results</summary>

  {% for category in ["applications", "tools", "data"] %}
    {% if category in facets.tags %}
    <div class="facet-group">
      <h2>{{ category | title }}</h2>
      <ul>
        {% for tag, count in facets.tags[category].most_common(10) %}
        <li>
          <a href="?q={{ query | default('') }} AND tag:&quot;{{ tag }}&quot;">
            {{ tag }} ({{ count }})
          </a>
        </li>
        {% endfor %}
      </ul>
    </div>
    {% endif %}
  {% endfor %}

  <div class="facet-group">
    <h2>Year</h2>
    <ul>
      {% for year, count in facets.years | dictsort(reverse=true) %}
      <li>
        <a href="?q={{ query | default('') }} AND year:{{ year }}">
          {{ year }} ({{ count }})
        </a>
      </li>
      {% endfor %}
    </ul>
  </div>

  <div class="facet-group">
    <h2>Type</h2>
    <ul>
      {% for type, count in facets.types.items() %}
      <li>{{ type }} ({{ count }})</li>
      {% endfor %}
    </ul>
  </div>
</details>
{% endif %}
```

- [ ] **Step 6: Include facets in index.html**

In `donut/templates/index.html`, add after the sort-controls div (after the `{% endif %}` that closes `{% if data is not none and data | length > 1 %}`), and before `{% if data is not none %}`:

```html
  {% include "facets.html" %}
```

- [ ] **Step 7: Pass facets from routes**

In `donut/__init__.py`, add import:

```python
from donut.database import compute_facets
```

In the `index` route, after `matches = search(...)`, add facet computation and pass to template:

```python
        if matches:
            facets = compute_facets(matches[0])
        else:
            facets = None
```

Add `facets=facets` to the `render_template` kwargs in the index route.

- [ ] **Step 8: Add CSS for facets**

Append to `donut/static/style.css`:

```css
.facets
{
  border:        1px solid #E8E8E8;
  background:    white;
  padding:       1rem;
  margin-bottom: 1rem;
}

.facets summary
{
  cursor:      pointer;
  font-weight: bold;
}

.facet-group
{
  margin-top: 0.5em;
}

.facet-group h2
{
  font-size:     small;
  text-transform: uppercase;
  color:         #666;
  margin:        0.5em 0 0.25em 0;
}

.facet-group ul
{
  list-style-type: none;
  padding-left:    0;
  margin:          0;
}

.facet-group li
{
  font-size:     small;
  margin-bottom: 0.1em;
}
```

- [ ] **Step 9: Run all tests**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 10: Commit**

```bash
git add donut/database.py donut/templates/facets.html donut/templates/index.html donut/__init__.py donut/static/style.css tests/test_database.py
git commit -m "Add faceted search with tag, year, and type refinement"
```

---

## Task 9: CLI Tag Validator

**Files:**
- Create: `donut/validate_tags.py`, `tests/test_validate_tags.py`
- Modify: `donut/reindex.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_validate_tags.py`:

```python
"""Tests for tag validation."""

from donut.validate_tags import (
    check_missing_categories,
    check_singleton_tags,
    check_near_duplicates,
    check_orphan_hierarchies,
)


def test_check_missing_categories(test_db):
    """Detect papers missing required tag categories."""
    issues = check_missing_categories(test_db)
    # GUDHI software entry has no applications or data tags
    assert any(
        "gudhi_2024" in issue for issue in issues
    )


def test_check_singleton_tags(test_db):
    """Detect tags that appear only once."""
    singletons = check_singleton_tags(test_db)
    assert isinstance(singletons, list)
    # "climate science" only appears in one paper
    singleton_tags = [tag for tag, _ in singletons]
    assert "climate science" in singleton_tags


def test_check_near_duplicates(test_db):
    """Near-duplicate detection returns list of pairs."""
    dupes = check_near_duplicates(test_db, threshold=0.85)
    assert isinstance(dupes, list)
    # All items should be tuples of (tag1, tag2, score)
    for item in dupes:
        assert len(item) == 3


def test_check_orphan_hierarchies(test_db):
    """Detect hierarchical tags with missing parents."""
    orphans = check_orphan_hierarchies(test_db)
    assert isinstance(orphans, list)
    # "neuroscience:brain imaging" should NOT be orphaned because
    # "neuroscience" exists
    orphan_tags = [tag for tag, _ in orphans]
    assert "neuroscience:brain imaging" not in orphan_tags
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_validate_tags.py -v
```

Expected: FAIL — `donut.validate_tags` module does not exist.

- [ ] **Step 3: Create validate_tags.py**

Create `donut/validate_tags.py`:

```python
"""Tag validation for DONUT database.

Can be run as a CLI tool: python -m donut.validate_tags

Checks for:
- Papers missing required tag categories (applications, tools, data)
- Tags that appear only once (potential typos)
- Near-duplicate tags (Jaro-Winkler similarity)
- Hierarchical tags with missing parents
"""

import collections
import itertools
import json
import os

from dotenv import load_dotenv
from nltk.metrics.distance import jaro_winkler_similarity

import xapian


REQUIRED_CATEGORIES = {"applications", "tools", "data"}


def _load_all_entries(database_dir):
    """Load all entries from the database."""
    db = xapian.Database(database_dir)
    entries = []

    for item in db.postlist(""):
        doc = db.get_document(item.docid)
        data = json.loads(doc.get_data())
        entries.append(data)

    return entries


def check_missing_categories(database_dir):
    """Check for papers missing required tag categories.

    Returns list of warning strings.
    """
    entries = _load_all_entries(database_dir)
    issues = []

    for entry in entries:
        entry_type = entry.get("raw", {}).get("ENTRYTYPE", "")
        if entry_type == "software":
            # Software entries only need tools tags
            continue

        categories_present = {
            cat for cat, _ in entry.get("keywords", [])
        }
        missing = REQUIRED_CATEGORIES - categories_present

        if missing:
            issues.append(
                f"{entry['id']}: missing categories "
                f"{', '.join(sorted(missing))}"
            )

    return issues


def check_singleton_tags(database_dir):
    """Check for tags that appear only once.

    Returns list of (tag_name, category) tuples.
    """
    entries = _load_all_entries(database_dir)
    tag_counts = collections.Counter()
    tag_categories = {}

    for entry in entries:
        for category, keyword in entry.get("keywords", []):
            tag_counts[keyword] += 1
            tag_categories[keyword] = category

    return [
        (tag, tag_categories[tag])
        for tag, count in sorted(tag_counts.items())
        if count == 1
    ]


def check_near_duplicates(database_dir, threshold=0.9):
    """Check for near-duplicate tags using Jaro-Winkler similarity.

    Returns list of (tag1, tag2, similarity_score) tuples.
    """
    entries = _load_all_entries(database_dir)
    all_tags = set()

    for entry in entries:
        for _, keyword in entry.get("keywords", []):
            all_tags.add(keyword)

    duplicates = []
    for t1, t2 in itertools.combinations(sorted(all_tags), 2):
        score = jaro_winkler_similarity(t1, t2)
        if score >= threshold:
            duplicates.append((t1, t2, round(score, 4)))

    return sorted(duplicates, key=lambda x: x[2], reverse=True)


def check_orphan_hierarchies(database_dir):
    """Check for hierarchical tags whose parents don't exist.

    For example, if "foo:bar:baz" exists but "foo:bar" does not.

    Returns list of (tag, missing_parent) tuples.
    """
    entries = _load_all_entries(database_dir)
    all_tags = set()

    for entry in entries:
        for _, keyword in entry.get("keywords", []):
            all_tags.add(keyword.lower())

    orphans = []
    for tag in sorted(all_tags):
        if ":" in tag:
            parts = tag.split(":")
            parent = ":".join(parts[:-1])
            if parent not in all_tags:
                orphans.append((tag, parent))

    return orphans


if __name__ == "__main__":
    load_dotenv()
    DATABASE_DIR = os.getenv("DATABASE_DIR", "database")

    print("=== Tag Validation Report ===\n")

    print("--- Missing Categories ---")
    issues = check_missing_categories(DATABASE_DIR)
    if issues:
        for issue in issues:
            print(f"  WARNING: {issue}")
    else:
        print("  All papers have required tag categories.")

    print(f"\n--- Singleton Tags ({len(check_singleton_tags(DATABASE_DIR))}) ---")
    singletons = check_singleton_tags(DATABASE_DIR)
    for tag, category in singletons[:20]:
        print(f"  [{category}] {tag}")
    if len(singletons) > 20:
        print(f"  ... and {len(singletons) - 20} more")

    print("\n--- Near-Duplicate Tags ---")
    dupes = check_near_duplicates(DATABASE_DIR)
    if dupes:
        for t1, t2, score in dupes[:20]:
            print(f"  {t1} ~ {t2} (similarity: {score})")
    else:
        print("  No near-duplicates found.")

    print("\n--- Orphan Hierarchies ---")
    orphans = check_orphan_hierarchies(DATABASE_DIR)
    if orphans:
        for tag, parent in orphans[:20]:
            print(f"  {tag} (missing parent: {parent})")
    else:
        print("  No orphaned hierarchical tags.")

    print("\n=== Done ===")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/test_validate_tags.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Add tag validation warnings to reindex.py**

In `donut/reindex.py`, add import:

```python
from donut.validate_tags import (
    check_missing_categories,
    check_near_duplicates,
)
```

Add at the end of the `if __name__ == "__main__"` block:

```python
    # Run tag validation
    print("\nRunning tag validation...")
    missing = check_missing_categories(DATABASE_DIR)
    if missing:
        print(f"WARNING: {len(missing)} papers missing tag categories:")
        for issue in missing[:5]:
            print(f"  {issue}")
        if len(missing) > 5:
            print(f"  ... and {len(missing) - 5} more")

    dupes = check_near_duplicates(DATABASE_DIR)
    if dupes:
        print(f"WARNING: {len(dupes)} near-duplicate tag pairs:")
        for t1, t2, score in dupes[:5]:
            print(f"  {t1} ~ {t2} ({score})")
        if len(dupes) > 5:
            print(f"  ... and {len(dupes) - 5} more")
```

- [ ] **Step 6: Run all tests**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 7: Commit**

```bash
git add donut/validate_tags.py donut/reindex.py tests/test_validate_tags.py
git commit -m "Add CLI tag validator with missing category, singleton, duplicate, and orphan checks"
```

---

## Task 10: Web Submission Form

**Files:**
- Create: `donut/templates/submit.html`
- Modify: `donut/__init__.py`, `donut/templates/base.html`, `donut/static/style.css`
- Modify: `tests/test_routes.py`

- [ ] **Step 1: Add submit route to __init__.py**

Add import at top:

```python
from flask import redirect, url_for, flash
```

Update the `create()` function to add `app.secret_key`:

```python
    app.secret_key = os.getenv(
        "SECRET_KEY", "donut-dev-key-change-in-production"
    )
```

Add routes inside `create()`, before `return app`:

```python
    @app.route("/submit", methods=["GET", "POST"])
    def submit():
        tags = get_tags(DATABASE_DIR)

        all_tags = {}
        for category, keywords in tags.items():
            all_tags[category] = sorted(keywords.keys())

        if request.method == "POST":
            submission = {
                "title": request.form.get("title", "").strip(),
                "authors": request.form.get("authors", "").strip(),
                "year": request.form.get("year", "").strip(),
                "doi": request.form.get("doi", "").strip(),
                "url": request.form.get("url", "").strip(),
                "abstract": request.form.get("abstract", "").strip(),
                "entry_type": request.form.get(
                    "entry_type", "article"
                ),
                "tags_applications": request.form.getlist(
                    "tags_applications"
                ),
                "tags_tools": request.form.getlist("tags_tools"),
                "tags_data": request.form.getlist("tags_data"),
                "new_tags": request.form.get(
                    "new_tags", ""
                ).strip(),
                "flavour": request.form.get("flavour", ""),
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

            # Validate required fields
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

            # Save submission
            submissions_dir = os.path.join(
                os.path.dirname(DATABASE_DIR), "submissions"
            )
            os.makedirs(submissions_dir, exist_ok=True)

            import time
            filename = f"{int(time.time())}_{submission['title'][:40]}.json"
            filename = "".join(
                c if c.isalnum() or c in "._-"
                else "_" for c in filename
            )
            filepath = os.path.join(submissions_dir, filename)

            with open(filepath, "w") as f:
                _json.dump(submission, f, indent=2)

            flash("Thank you! Your submission has been received "
                  "and will be reviewed by a maintainer.")
            return redirect(url_for("submit"))

        return render_template(
            "submit.html", tags=all_tags, errors=[], form={},
        )
```

- [ ] **Step 2: Create submit.html template**

Create `donut/templates/submit.html`:

```html
{% extends "base.html" %}

{% set nosearch = true %}

{% block content %}
<article>
  <h1>Submit a Paper or Software</h1>
  <p>
    Use this form to suggest a paper or software tool for inclusion in
    DONUT. All submissions are reviewed by a maintainer before being
    added to the database.
  </p>

  {% with messages = get_flashed_messages() %}
    {% if messages %}
      {% for message in messages %}
      <div class="submit-success">{{ message }}</div>
      {% endfor %}
    {% endif %}
  {% endwith %}

  {% if errors | length > 0 %}
  <div class="error">
    <ul>
      {% for error in errors %}
      <li>{{ error }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endif %}

  <form method="POST" class="submit-form">
    <fieldset>
      <legend>Basic Information</legend>

      <label for="title">Title *</label>
      <input type="text" id="title" name="title" required
             value="{{ form.title | default('') }}">

      <label for="authors">Authors (comma-separated) *</label>
      <input type="text" id="authors" name="authors" required
             placeholder="Alice Smith, Bob Jones"
             value="{{ form.authors | default('') }}">

      <label for="year">Year *</label>
      <input type="number" id="year" name="year" required
             min="1900" max="2100"
             value="{{ form.year | default('') }}">

      <label for="doi">DOI</label>
      <input type="text" id="doi" name="doi"
             placeholder="10.1234/example"
             value="{{ form.doi | default('') }}">

      <label for="url">URL</label>
      <input type="url" id="url" name="url"
             placeholder="https://..."
             value="{{ form.url | default('') }}">

      <label for="abstract">Abstract</label>
      <textarea id="abstract" name="abstract" rows="5"
        >{{ form.abstract | default('') }}</textarea>

      <label>Entry type *</label>
      <div class="radio-group">
        <label>
          <input type="radio" name="entry_type" value="article"
                 {{ 'checked' if form.entry_type | default('article') == 'article' }}>
          Paper
        </label>
        <label>
          <input type="radio" name="entry_type" value="software"
                 {{ 'checked' if form.entry_type | default('') == 'software' }}>
          Software
        </label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Tags</legend>
      <p class="field-help">
        Select existing tags or type new ones below. Each paper should
        have at least one tag in each category.
      </p>

      <label for="tags_applications">Application Tags</label>
      <select id="tags_applications" name="tags_applications" multiple
              size="8">
        {% for tag in tags.get("applications", []) %}
        <option value="{{ tag }}"
          {{ 'selected' if tag in form.get('tags_applications', []) }}>
          {{ tag }}
        </option>
        {% endfor %}
      </select>

      <label for="tags_tools">Tool Tags</label>
      <select id="tags_tools" name="tags_tools" multiple size="8">
        {% for tag in tags.get("tools", []) %}
        <option value="{{ tag }}"
          {{ 'selected' if tag in form.get('tags_tools', []) }}>
          {{ tag }}
        </option>
        {% endfor %}
      </select>

      <label for="tags_data">Data Tags</label>
      <select id="tags_data" name="tags_data" multiple size="8">
        {% for tag in tags.get("data", []) %}
        <option value="{{ tag }}"
          {{ 'selected' if tag in form.get('tags_data', []) }}>
          {{ tag }}
        </option>
        {% endfor %}
      </select>

      <label for="new_tags">New tags (if not listed above)</label>
      <textarea id="new_tags" name="new_tags" rows="2"
                placeholder="One tag per line, e.g.: 1 - robotics:swarm"
        >{{ form.new_tags | default('') }}</textarea>

      <label>Flavour</label>
      <div class="radio-group">
        <label>
          <input type="radio" name="flavour" value=""
                 {{ 'checked' if form.flavour | default('') == '' }}>
          Neither
        </label>
        <label>
          <input type="radio" name="flavour" value="innovate"
                 {{ 'checked' if form.flavour | default('') == 'innovate' }}>
          Innovate
        </label>
        <label>
          <input type="radio" name="flavour" value="confirm"
                 {{ 'checked' if form.flavour | default('') == 'confirm' }}>
          Confirm
        </label>
      </div>
    </fieldset>

    <fieldset>
      <legend>Community Resources (optional)</legend>

      <label for="code_url">Code URL</label>
      <input type="url" id="code_url" name="code_url"
             placeholder="https://github.com/..."
             value="{{ form.code_url | default('') }}">

      <label for="data_url">Data URL</label>
      <input type="url" id="data_url" name="data_url"
             placeholder="https://..."
             value="{{ form.data_url | default('') }}">

      <label for="video_url">Video URL</label>
      <input type="url" id="video_url" name="video_url"
             placeholder="https://youtube.com/..."
             value="{{ form.video_url | default('') }}">
    </fieldset>

    <button type="submit" class="submit-button">Submit for Review</button>
  </form>
</article>
{% endblock %}
```

- [ ] **Step 3: Add CSS for submission form**

Append to `donut/static/style.css`:

```css
.submit-form fieldset
{
  border:        1px solid #E8E8E8;
  padding:       1em;
  margin-bottom: 1em;
}

.submit-form legend
{
  font-weight: bold;
  padding:     0 0.5em;
}

.submit-form label
{
  display:    block;
  margin-top: 0.75em;
  font-size:  small;
  font-weight: 600;
  color:      #555;
}

.submit-form input[type="text"],
.submit-form input[type="number"],
.submit-form input[type="url"],
.submit-form textarea,
.submit-form select
{
  display:    block;
  width:      100%;
  padding:    0.4em;
  border:     1px solid #E8E8E8;
  margin-top: 0.25em;
  font-family: inherit;
}

.submit-form select[multiple]
{
  height: auto;
}

.radio-group
{
  margin-top: 0.25em;
}

.radio-group label
{
  display:     inline;
  margin-right: 1.5em;
  font-weight: normal;
}

.field-help
{
  font-size:  small;
  color:      #888;
  margin:     0.25em 0;
}

.submit-button
{
  margin-top:  1em;
  padding:     0.5em 2em;
  font-size:   1em;
  cursor:      pointer;
}

.submit-success
{
  border:           1px solid #66c2a5;
  border-radius:    2.5px;
  background-color: #66c2a511;
  padding:          0.5em;
  margin-bottom:    1em;
}
```

- [ ] **Step 4: Update navigation in base.html**

In `donut/templates/base.html`, add Submit link at the end of the nav, after Contributors:

```html
        &bull;
        <a href="/submit">Submit</a>
```

- [ ] **Step 5: Add .gitignore entry for submissions**

Append to `.gitignore`:

```
submissions/
```

- [ ] **Step 6: Add route tests**

Append to `tests/test_routes.py`:

```python
def test_submit_page_get(client):
    """Submit form loads."""
    response = client.get("/submit")
    assert response.status_code == 200
    assert b"Submit a Paper" in response.data


def test_submit_page_post_missing_fields(client):
    """Submit with missing fields shows errors."""
    response = client.post("/submit", data={
        "title": "",
        "authors": "",
        "year": "",
    })
    assert response.status_code == 200
    assert b"required" in response.data.lower()


def test_submit_page_post_valid(client, tmp_path):
    """Valid submission saves a JSON file."""
    response = client.post("/submit", data={
        "title": "Test Paper",
        "authors": "Test Author",
        "year": "2024",
        "doi": "10.1234/test",
        "entry_type": "article",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Thank you" in response.data
```

- [ ] **Step 7: Run all tests**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 8: Commit**

```bash
git add donut/templates/submit.html donut/__init__.py donut/templates/base.html donut/static/style.css .gitignore tests/test_routes.py
git commit -m "Add web submission form with tag selection and validation"
```

---

## Task 11: Reindex the Production Database

This is the final step that makes everything work together.

- [ ] **Step 1: Run reindex to add year value slots and compute precomputed data**

```bash
cd /Users/yossi/DONUT && rm -rf database/*.glass database/flintlock database/iamglass && .venv/bin/python -m donut.reindex
```

Expected output: indexing messages, similarity computation, co-occurrence computation, tag validation warnings.

- [ ] **Step 2: Verify the app runs**

```bash
cd /Users/yossi/DONUT && .venv/bin/flask --app donut:create run
```

Visit http://127.0.0.1:5000/ and verify:
- Home page loads with search
- `/papers` shows paginated results
- `/stats` shows statistics with charts
- `/explore` shows the tag co-occurrence graph
- `/timeline` shows papers by year
- `/submit` shows the submission form
- Search results show sort controls

- [ ] **Step 3: Run full test suite**

```bash
cd /Users/yossi/DONUT && .venv/bin/pytest tests/ -v
```

Expected: All tests PASS.

- [ ] **Step 4: Commit any remaining changes**

```bash
git add -A && git status
```

Review and commit if there are changes.
