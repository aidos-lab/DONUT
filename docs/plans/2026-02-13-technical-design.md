# DONUT Technical Design

**Date:** 2026-02-13
**Authors:** Yossi Bokor Bleile
**Companion:** See `2026-02-13-roadmap.md` for high-level roadmap

This document provides implementation-level detail for each roadmap item.
All references are to the current codebase structure.

---

## Architecture Context

```
Current request flow:

  Browser --> Flask route (donut/__init__.py)
                |
                +--> database.py (Xapian queries)
                |      |
                |      +--> Xapian DB (database/*.glass)
                |
                +--> templates/*.html (Jinja2 rendering)
```

**Key constraints:**
- Xapian has no built-in JSON API; all serialization is manual
- Documents store full entry JSON in `doc.set_data()` (database.py:81)
- Tags are stored in keywords with category prefixes (parse_bibtex.py:168)
- No JavaScript currently; all rendering is server-side

---

## Phase 1: Foundation & Quick Wins

### 1.1 REST API

**Files to modify:**
- `donut/__init__.py` (add routes)
- `donut/database.py` (add JSON-friendly return helpers)

**New routes:**

```python
# donut/__init__.py — add inside create()

from flask import jsonify

@app.route("/api/papers")
def api_papers():
    """Return papers as JSON. Supports query params for filtering."""
    query = request.args.get("q", "")
    tag = request.args.get("tag", "")
    author = request.args.get("author", "")
    year = request.args.get("year", "")

    # Build query string from params
    parts = []
    if query:
        parts.append(query)
    if tag:
        parts.append(f'tag:"{tag}"')
    if author:
        parts.append(f'author:"{author}"')
    if year:
        parts.append(f'year:{year}')

    query_str = " AND ".join(parts) if parts else None

    if query_str:
        matches = search(DATABASE_DIR, query_str)
        data = matches[0] if matches else []
    else:
        data = get_documents(DATABASE_DIR)
        data = [m for m in data
                if m["document"]["raw"]["ENTRYTYPE"] != "software"]

    # Strip raw BibTeX from API response (redundant, large)
    for item in data:
        item["document"].pop("raw", None)

    return jsonify({
        "count": len(data),
        "results": data,
    })


@app.route("/api/papers/<int:identifier>")
def api_paper(identifier):
    """Return single paper as JSON."""
    doc = get_document(DATABASE_DIR, identifier)
    doc["document"].pop("raw", None)
    return jsonify(doc)


@app.route("/api/tags")
def api_tags():
    """Return tag hierarchy with counts."""
    tags = get_tags(DATABASE_DIR)
    # Convert Counter objects to plain dicts for JSON
    result = {
        category: dict(sorted(keywords.items()))
        for category, keywords in sorted(tags.items())
    }
    return jsonify(result)
```

**CORS:** Add `flask-cors` or a simple `@app.after_request` handler:

```python
@app.after_request
def add_cors_headers(response):
    if request.path.startswith("/api/"):
        response.headers["Access-Control-Allow-Origin"] = "*"
    return response
```

**No new dependencies required** (Flask's `jsonify` handles serialization).

---

### 1.2 Result Sorting

**Problem:** `get_documents()` (database.py:167) iterates `db.postlist("")`
which returns documents in docid order. Search results from `search()`
(database.py:97) return in Xapian relevance order. Neither supports
year-based sorting.

**Solution:** Store `year` as a Xapian value slot for sort-by-value.

**Files to modify:**
- `donut/database.py` — indexing and querying
- `donut/__init__.py` — pass sort parameter to templates
- `donut/templates/index.html` — sort controls UI
- `donut/templates/search.html` — add sort hidden input

**Indexing change** (database.py, inside `index_documents`):

```python
# After line 81 (doc.set_data), add:
SLOT_YEAR = 0

year = entry.get("year", "0000")
doc.add_value(SLOT_YEAR, xapian.sortable_serialise(int(year)))
```

**Query change** (database.py, modify `search` signature):

```python
def search(database_dir, query_str, sort_by=None, reverse=True):
    # ... existing code through line 145 ...

    if sort_by == "year":
        enquire.set_sort_by_value_then_relevance(
            SLOT_YEAR, reverse  # True = newest first
        )
    # Default: relevance (no change needed)

    # ... rest of function ...
```

**Template change** (index.html, after query-statistics div):

```html
{% if data is not none and data | length > 1 %}
<div class="sort-controls">
  Sort by:
  <a href="?q={{ query }}&sort=relevance">Relevance</a> |
  <a href="?q={{ query }}&sort=year_desc">Newest</a> |
  <a href="?q={{ query }}&sort=year_asc">Oldest</a>
</div>
{% endif %}
```

**Reindex required:** Yes. Run `python -m donut.reindex` after deploying
the indexing change.

---

### 1.3 Pagination

**Problem:** `search()` calls `enquire.get_mset(0, n_documents)` fetching
all results (database.py:150-153). `/papers` and `/software` call
`get_documents()` which iterates the entire postlist (database.py:173).

**Solution:** Add `offset` and `limit` parameters throughout.

**database.py changes:**

```python
PAGE_SIZE = 25

def search(database_dir, query_str, sort_by=None, reverse=True,
           offset=0, limit=PAGE_SIZE):
    # ... existing setup ...

    # Replace lines 150-154:
    total_count = enquire.get_mset(0, 0).get_matches_estimated()

    matches = []
    for match in enquire.get_mset(offset, limit):
        matches.append(_build_match(match.document))

    return matches, corrected_query, total_count


def get_documents(database_dir, offset=0, limit=PAGE_SIZE,
                  entry_type=None):
    """Return documents with pagination and optional type filter."""
    db = xapian.Database(database_dir)
    matches = []
    skipped = 0
    count = 0

    for item in db.postlist(""):
        document = db.get_document(item.docid)
        data = json.loads(document.get_data())

        # Filter by entry type if specified
        if entry_type and data["raw"]["ENTRYTYPE"] != entry_type:
            continue

        if skipped < offset:
            skipped += 1
            continue

        matches.append(_build_match(document))
        count += 1

        if count >= limit:
            break

    return matches
```

**Route changes** (__init__.py):

```python
@app.route("/papers")
def papers():
    page = request.args.get("page", 1, type=int)
    offset = (page - 1) * PAGE_SIZE

    matches = get_documents(DATABASE_DIR, offset=offset,
                            entry_type="article")  # != software
    total = get_num_documents(DATABASE_DIR)  # Approximate

    return render_template(
        "index.html",
        data=matches,
        page=page,
        total_pages=(total // PAGE_SIZE) + 1,
    )
```

**Template pagination controls** (add to bottom of index.html):

```html
{% if total_pages is defined and total_pages > 1 %}
<nav class="pagination">
  {% if page > 1 %}
    <a href="?page={{ page - 1 }}">&laquo; Previous</a>
  {% endif %}
  Page {{ page }} of {{ total_pages }}
  {% if page < total_pages %}
    <a href="?page={{ page + 1 }}">Next &raquo;</a>
  {% endif %}
</nav>
{% endif %}
```

**Note:** For search results, Xapian's `get_mset(offset, limit)` handles
pagination natively and efficiently. For browse pages (`/papers`,
`/software`), the postlist iteration is less efficient but acceptable
at current scale.

---

### 1.4 RSS Feed

**New file:** `donut/feed.py` (or add to __init__.py)

**Approach:** Generate an Atom feed from the most recently added papers.
Since BibTeX entries don't have an "added date," use the year field as
a proxy, or better, track addition dates via git.

**Minimal implementation (no new dependencies):**

```python
# donut/__init__.py — add route
from markupsafe import escape
from flask import Response

@app.route("/feed")
def feed():
    matches = get_documents(DATABASE_DIR)
    # Filter to papers only, sort by year descending
    papers = [m for m in matches
              if m["document"]["raw"]["ENTRYTYPE"] != "software"]
    papers.sort(key=lambda m: m["document"].get("year", "0"), reverse=True)
    papers = papers[:20]  # Latest 20

    entries_xml = []
    for p in papers:
        doc = p["document"]
        title = escape(doc["title"])
        abstract = escape(doc.get("abstract", "")[:500])
        entry_id = escape(doc["id"])
        year = escape(doc.get("year", "2020"))
        entry_xml = (
            f"<entry>"
            f"<title>{title}</title>"
            f"<id>urn:donut:{entry_id}</id>"
            f"<updated>{year}-01-01T00:00:00Z</updated>"
            f"<summary>{abstract}</summary>"
            f"<link href=\"https://donut.topology.rocks/?q={entry_id}\" />"
            f"</entry>"
        )
        entries_xml.append(entry_xml)

    feed_xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        '<feed xmlns="http://www.w3.org/2005/Atom">'
        '<title>DONUT: Applied Topology Papers</title>'
        '<link href="https://donut.topology.rocks/feed" rel="self" />'
        '<link href="https://donut.topology.rocks/" />'
        '<id>urn:donut:feed</id>'
        '<updated>2026-01-01T00:00:00Z</updated>'
        + "".join(entries_xml)
        + '</feed>'
    )

    return Response(feed_xml, mimetype="application/atom+xml")
```

**Better approach for accurate dates:** Add a `date-added` Zotero field,
or parse git log for each `.bib` file's first commit date during indexing.

---

### 1.5 Bulk BibTeX Export

**Files to modify:**
- `donut/__init__.py` (new route)

```python
@app.route("/export-all")
def export_all():
    """Export all papers matching current query as single .bib file."""
    query = request.args.get("q", "")

    if query:
        matches = search(DATABASE_DIR, query)
        data = matches[0] if matches else []
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

**Template change** (index.html, after query-statistics):

```html
{% if data is not none and data | length > 0 %}
  <a href="{{ url_for('export_all', q=query) }}">
    Export all {{ data | length }} results as BibTeX
  </a>
{% endif %}
```

---

## Phase 2: Enhanced Search & Filtering

### 2.1 Faceted Search Sidebar

**Concept:** After a search, compute tag/year/type distributions from the
result set and display as clickable filters.

**New function** (database.py):

```python
def compute_facets(matches):
    """Compute facets from a list of match dicts."""
    tag_counts = collections.defaultdict(
        lambda: collections.Counter()
    )
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
        "years": dict(year_counts.most_common()),
        "types": dict(type_counts),
    }
```

**Route change** (__init__.py, modify index route):

```python
# After getting matches, compute facets
if matches:
    facets = compute_facets(matches[0])
else:
    facets = None

return render_template(
    "index.html",
    data=matches[0] if matches else None,
    facets=facets,
    # ... existing params ...
)
```

**New template partial** `templates/facets.html`:

```html
{% if facets %}
<aside class="facets">
  <h2>Refine results</h2>

  {% for category in ["applications", "tools", "data"] %}
    {% if category in facets.tags %}
    <details open>
      <summary>{{ category | title }}</summary>
      <ul>
        {% for tag, count in facets.tags[category].most_common(10) %}
        <li>
          <a href="?q={{ query }} AND tag:&quot;{{ tag }}&quot;">
            {{ tag }} ({{ count }})
          </a>
        </li>
        {% endfor %}
      </ul>
    </details>
    {% endif %}
  {% endfor %}

  <details>
    <summary>Year</summary>
    <ul>
      {% for year, count in facets.years %}
      <li>
        <a href="?q={{ query }} AND year:{{ year }}">
          {{ year }} ({{ count }})
        </a>
      </li>
      {% endfor %}
    </ul>
  </details>
</aside>
{% endif %}
```

**CSS addition** (style.css):

```css
.facets {
  border: 1px solid #E8E8E8;
  background: white;
  padding: 1rem;
  margin-bottom: 1rem;
}

.facets ul {
  list-style-type: none;
  padding-left: 0;
}

.facets li {
  margin-bottom: 0.25em;
}
```

**Layout consideration:** The current `max-width: 80ch` layout doesn't
have room for a sidebar. Two options:
1. **Above results** (simplest): Show facets as a collapsible section
   above the result list. No layout changes needed.
2. **Sidebar** (better UX): Increase max-width and use CSS grid. Larger
   change but standard pattern.

Recommendation: Start with option 1, iterate to option 2 if users want it.

---

### 2.2 Search Autocomplete

**New API endpoint** (donut/__init__.py):

```python
@app.route("/api/suggest")
def api_suggest():
    """Return search suggestions for autocomplete."""
    q = request.args.get("q", "").strip().lower()
    if len(q) < 2:
        return jsonify([])

    db = xapian.Database(DATABASE_DIR)
    suggestions = set()

    # Suggest from tag terms (K prefix)
    for term in db.allterms("K"):
        decoded = term.term.decode("utf-8")[1:]  # Strip K prefix
        if q in decoded.lower():
            suggestions.add(f'tag:"{decoded}"')
            if len(suggestions) >= 10:
                break

    # Suggest from author terms (A prefix)
    for term in db.allterms("A"):
        decoded = term.term.decode("utf-8")[1:]  # Strip A prefix
        if q in decoded.lower():
            suggestions.add(f'author:"{decoded}"')
            if len(suggestions) >= 15:
                break

    return jsonify(sorted(suggestions)[:10])
```

**Frontend** (search.html, add after input):

Use safe DOM manipulation (no innerHTML) to prevent XSS:

```html
<input type="text" name="query" id="query-input"
       autocomplete="off" autofocus
       value="{{ query if query is defined else '' }}" />
<ul id="suggestions" style="display:none;"></ul>

<script>
const input = document.getElementById('query-input');
const suggestionsEl = document.getElementById('suggestions');

let debounce;
input.addEventListener('input', function() {
  clearTimeout(debounce);
  debounce = setTimeout(async () => {
    const q = input.value.trim();
    if (q.length < 2) { suggestionsEl.style.display = 'none'; return; }

    const resp = await fetch('/api/suggest?q=' + encodeURIComponent(q));
    const items = await resp.json();

    if (items.length === 0) { suggestionsEl.style.display = 'none'; return; }

    // Safe DOM construction (no innerHTML)
    suggestionsEl.replaceChildren();
    for (const s of items) {
      const li = document.createElement('li');
      const a = document.createElement('a');
      a.href = '/?q=' + encodeURIComponent(s);
      a.textContent = s;
      li.appendChild(a);
      suggestionsEl.appendChild(li);
    }
    suggestionsEl.style.display = 'block';
  }, 200);
});

document.addEventListener('click', (e) => {
  if (!suggestionsEl.contains(e.target)) suggestionsEl.style.display = 'none';
});
</script>
```

This is ~25 lines of vanilla JS with no dependencies and no XSS risk.

---

### 2.3 Year Range Filtering

**Approach:** Use Xapian value range queries with the year value slot
from Phase 1.2.

**database.py addition:**

```python
def search(database_dir, query_str, sort_by=None, reverse=True,
           offset=0, limit=PAGE_SIZE, year_from=None, year_to=None):
    # ... existing setup ...

    if year_from or year_to:
        vrp = xapian.NumberValueRangeProcessor(SLOT_YEAR)
        queryparser.add_valuerangeprocessor(vrp)

    # ... parse query ...

    # Add year range filter if specified
    if year_from or year_to:
        yr_from = xapian.sortable_serialise(int(year_from or 1900))
        yr_to = xapian.sortable_serialise(int(year_to or 2100))
        year_query = xapian.Query(
            xapian.Query.OP_VALUE_RANGE, SLOT_YEAR, yr_from, yr_to
        )
        query = xapian.Query(
            xapian.Query.OP_FILTER, query, year_query
        )

    enquire.set_query(query)
    # ... rest of function ...
```

**Template:** Add year range inputs to the search form or facets panel.

---

## Phase 3: Discovery & Exploration

### 3.1 Related Papers

**New module:** `donut/similarity.py`

```python
"""Compute paper similarity for 'related papers' feature."""

import json
import xapian


def compute_similarity_matrix(database_dir):
    """Compute Jaccard tag similarity between all paper pairs.

    Returns dict mapping docid -> list of (docid, score) tuples,
    sorted by score descending, limited to top 5.
    """
    db = xapian.Database(database_dir)
    papers = {}

    # Collect tag sets per document
    for item in db.postlist(""):
        doc = db.get_document(item.docid)
        data = json.loads(doc.get_data())
        tag_set = frozenset(kw for _, kw in data.get("keywords", []))
        papers[item.docid] = tag_set

    # Compute pairwise Jaccard similarity
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
                if jaccard > 0.1:  # Threshold to reduce noise
                    scores.append((id_b, jaccard))

        scores.sort(key=lambda x: x[1], reverse=True)
        neighbors[id_a] = scores[:5]

    return neighbors
```

**Integration options:**

1. **Precompute at index time:** Run during `reindex.py`, store as a JSON
   file (`database/similarity.json`). Load into memory at app startup.
   At 554 papers, the file is ~50KB.

2. **Store in Xapian:** Add similarity data as a document value slot.
   More integrated but harder to update.

Recommendation: Option 1 (JSON file). Simplest, decoupled from Xapian.

**Template change** (index.html, inside each result article):

```html
{% if related_papers is defined and id in related_papers %}
<details>
  <summary>Related papers</summary>
  <ul>
    {% for rel_id, score in related_papers[id] %}
      <li><a href="/?q=...">{{ rel_title }}</a></li>
    {% endfor %}
  </ul>
</details>
{% endif %}
```

**Performance:** 554^2 / 2 = ~153K comparisons. Each is a set
intersection, which is O(n) where n = average tag count (~5).
Total: ~750K operations. Runs in <1 second on any modern machine.

---

### 3.2 Tag Co-occurrence Visualization

**New route and template:**

```python
@app.route("/explore")
def explore():
    """Interactive tag co-occurrence explorer."""
    cooccurrence = compute_tag_cooccurrence(DATABASE_DIR)
    return render_template("explore.html", data=cooccurrence)
```

**New function** (database.py or new `donut/analysis.py`):

```python
def compute_tag_cooccurrence(database_dir):
    """Compute tag co-occurrence matrix.

    Returns list of {source, target, weight} dicts for graph edges.
    """
    db = xapian.Database(database_dir)
    pair_counts = collections.Counter()

    for item in db.postlist(""):
        doc = db.get_document(item.docid)
        data = json.loads(doc.get_data())
        tags = [kw for _, kw in data.get("keywords", [])]

        # Count all pairs
        for i in range(len(tags)):
            for j in range(i + 1, len(tags)):
                pair = tuple(sorted([tags[i], tags[j]]))
                pair_counts[pair] += 1

    # Filter to pairs with >= 3 co-occurrences (reduce noise)
    edges = []
    for (source, target), weight in pair_counts.items():
        if weight >= 3:
            edges.append({
                "source": source,
                "target": target,
                "weight": weight,
            })

    return edges
```

**Frontend:** Use D3.js force-directed graph. This is the one place
where a JS library is justified --- network graphs are fundamentally
interactive. Load D3 from CDN (no npm/bundler needed).

The template (`explore.html`) should receive data via `{{ data | tojson }}`
(Jinja2's tojson filter auto-escapes for safe embedding in script
contexts). Use D3's safe DOM manipulation methods (`.append()`,
`.attr()`, `.text()`) --- never set content via innerHTML.

**Also expose as API** for programmatic access:

```python
@app.route("/api/tag-cooccurrence")
def api_tag_cooccurrence():
    return jsonify(compute_tag_cooccurrence(DATABASE_DIR))
```

---

### 3.3 Timeline View

**New route:**

```python
@app.route("/timeline")
def timeline():
    """Papers plotted by year and domain."""
    matches = get_documents(DATABASE_DIR)
    papers = [m for m in matches
              if m["document"]["raw"]["ENTRYTYPE"] != "software"]

    # Group by year, with primary application tag
    by_year = collections.defaultdict(list)
    for p in papers:
        doc = p["document"]
        year = doc.get("year", "unknown")
        app_tags = [kw for cat, kw in doc.get("keywords", [])
                    if cat == "applications"]
        primary_tag = app_tags[0] if app_tags else "untagged"
        by_year[year].append({
            "title": doc["title"],
            "tag": primary_tag,
            "id": p["id"],
        })

    return render_template("timeline.html",
                           by_year=dict(sorted(by_year.items())))
```

Can render as:
- **Server-side HTML** (zero JS): Year headings with paper lists, colored
  by domain. Works immediately.
- **D3/Chart.js visualization:** Stacked bar chart or scatter plot. Add
  as progressive enhancement.

---

### 3.4 Paper Statistics Dashboard

**New route:**

```python
@app.route("/stats")
def stats():
    matches = get_documents(DATABASE_DIR)
    papers = [m for m in matches
              if m["document"]["raw"]["ENTRYTYPE"] != "software"]

    # Compute statistics
    years = collections.Counter()
    tags = collections.Counter()
    authors = collections.Counter()

    for p in papers:
        doc = p["document"]
        years[doc.get("year", "?")] += 1
        for _, kw in doc.get("keywords", []):
            tags[kw] += 1
        for author in doc.get("author", []):
            authors[author] += 1

    return render_template("stats.html",
                           years=dict(sorted(years.items())),
                           top_tags=tags.most_common(20),
                           top_authors=authors.most_common(20),
                           total=len(papers))
```

No JS required. Render as HTML tables/lists. Optionally add Chart.js
bar charts as progressive enhancement.

---

## Phase 4: Software Catalog & Cross-Referencing

### 4.1 Expand Software Catalog

**This is primarily a data/curation task.** The existing BibTeX `software`
entry type (used by `parse_bibtex.py:242`) already supports it.

**New keyword categories** (add to `parse_bibtex.py:168`):

```python
category_map = {
    "1": "applications",
    "2": "tools",
    "3": "data",
    "4": "language",     # NEW: Programming language
    "5": "platform",     # NEW: OS/platform
}
```

**Example new software entry:**

```bibtex
@software{gudhi_2024,
  author   = {{GUDHI Project}},
  title    = {GUDHI Library},
  year     = {2024},
  url      = {https://gudhi.inria.fr/},
  keywords = {
    2 - Persistent homology,
    2 - Simplicial complex,
    2 - Alpha complex,
    3 - Point cloud,
    4 - C++,
    4 - Python,
    C-https://github.com/GUDHI/gudhi-devel GitHub
  },
  abstract = {GUDHI is an open source library for Computational
              Topology and Topological Data Analysis.},
}
```

**Template enhancement** for software entries (index.html):
Add language/platform badges similar to the existing tag display, with
a new color:

```css
span.inline-tag-language {
  background: #e78ac3;  /* Pink */
}

span.inline-tag-platform {
  background: #a6d854;  /* Green */
}
```

---

### 4.2 Software-Paper Cross-Referencing

**Approach:** Add a new keyword category for software tools used by a paper.

```
S - GUDHI
S - Ripser
```

This maps to category "software_used" in the keyword parser. Papers
tagged this way become searchable via `tag:GUDHI`.

**New keyword category** (parse_bibtex.py):

```python
category_map = {
    "1": "applications",
    "2": "tools",
    "3": "data",
    "4": "language",
    "5": "platform",
    "6": "software_used",
}
```

**Template addition:** On each paper card, show "Built with:" section
listing linked software tools. On each software entry, show "Used by
N papers" with a link to the filtered search.

---

### 4.3 Tool Comparison Page

**New route:**

```python
@app.route("/software/compare")
def software_compare():
    """Feature comparison matrix for TDA software."""
    software = get_documents(DATABASE_DIR)
    software = [m for m in software
                if m["document"]["raw"]["ENTRYTYPE"] == "software"]

    # Build feature matrix
    all_features = set()
    tool_features = {}

    for s in software:
        doc = s["document"]
        name = doc["title"]
        features = set()
        for cat, kw in doc.get("keywords", []):
            if cat in ("tools", "data", "language"):
                features.add((cat, kw))
                all_features.add((cat, kw))
        tool_features[name] = features

    return render_template("compare.html",
                           tools=tool_features,
                           features=sorted(all_features))
```

**Template:** Render as an HTML table with tools as columns, features as
rows, and checkmarks for supported features. Pure HTML, no JS needed.

---

## Migration & Deployment Notes

### Reindexing

Phases 1.2, 2.3, and 3.1 require changes to the Xapian index schema
(new value slots). After deploying these changes:

```bash
# Remove old database
rm -rf database/

# Rebuild from BibTeX files
python -m donut.reindex
```

This takes <10 seconds for 554 papers. No downtime if you build to a
new directory and swap atomically.

### New Navigation

After Phase 3, the nav bar grows. Proposed update:

```
Home | Papers | Software | Tags | Explore | Timeline | Stats | FAQ
```

Consider grouping under dropdowns if it gets crowded.

### Deployment

No infrastructure changes needed. The existing Gunicorn + Nginx setup
handles all new routes. The only external resource is the D3.js CDN for
Phase 3.2 (tag co-occurrence graph).

### Testing

Each phase should include:

1. **Manual smoke test:** Verify all existing routes still work
2. **Search regression:** Run a set of known queries and verify results
   haven't changed
3. **New feature verification:** Test each new endpoint/page

Consider adding a `tests/` directory with pytest and Flask's test client:

```python
def test_api_papers(client):
    response = client.get("/api/papers")
    assert response.status_code == 200
    data = response.get_json()
    assert "count" in data
    assert "results" in data
```

---

## File Change Summary

| File | Phase | Changes |
|------|-------|---------|
| `donut/__init__.py` | 1.1-1.5, 2.1-2.2, 3.1-3.4, 4.3 | New routes, facet computation |
| `donut/database.py` | 1.2-1.3, 2.1, 2.3, 3.2 | Sort slots, pagination, facets, co-occurrence |
| `donut/parse_bibtex.py` | 4.1-4.2 | New keyword categories |
| `donut/similarity.py` | 3.1 | **New file** --- similarity computation |
| `donut/templates/index.html` | 1.2-1.3, 1.5, 2.1, 3.1 | Sort, pagination, export link, facets, related |
| `donut/templates/search.html` | 2.2 | Autocomplete JS |
| `donut/templates/explore.html` | 3.2 | **New file** --- D3 tag graph |
| `donut/templates/timeline.html` | 3.3 | **New file** --- timeline view |
| `donut/templates/stats.html` | 3.4 | **New file** --- statistics dashboard |
| `donut/templates/compare.html` | 4.3 | **New file** --- software comparison |
| `donut/templates/base.html` | 3.x | Updated navigation |
| `donut/static/style.css` | 1.3, 2.1, 4.1 | Pagination, facets, new tag colors |
| `donut/reindex.py` | 1.2, 3.1 | Trigger similarity computation after index |
