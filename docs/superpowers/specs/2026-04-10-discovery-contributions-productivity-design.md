# DONUT Improvement Design: Discovery, Contributions & Productivity

**Date:** 2026-04-10
**Authors:** Yossi Bokor Bleile
**Status:** Approved
**Priority order:** Discovery & Exploration > Contributor Experience > Researcher Productivity

---

## Context

DONUT is a curated search engine for applications of Topological Data Analysis,
built with Flask + Xapian, currently serving ~554 BibTeX entries sourced from a
Zotero group. It serves two audiences equally: domain experts looking for "has
TDA been applied to my field?" and TDA researchers exploring which methods are
used and where.

**Current pain points:**
- No discovery features beyond keyword search -- researchers can't stumble into
  connections
- Contributor workflow is slow (manual Zotero entry from Google Form submissions)
  with no tag validation, leading to tag inconsistency
- No sorting, pagination, or filtering on browse pages

**Guiding principles (carried from existing roadmap):**
- Minimal dependencies: Flask + Xapian, no JS frameworks, CDN-loaded chart libs
- Backwards compatible: preserve existing URL patterns and search syntax
- Privacy-first: no accounts, no tracking, no cookies
- Curation over automation: features enhance discovery within the curated set

---

## Section 1: Discovery Features

### 1.1 Tag Co-occurrence Explorer (`/explore`)

The centrepiece discovery feature. An interactive force-directed network graph.

**Nodes:** Tags, sized by frequency, colored by category:
- Green (#66c2a5) for applications
- Orange (#fc8d62) for tools
- Blue (#8da0cb) for data

**Edges:** Co-occurrence links. Thickness proportional to how often two tags
appear on the same paper. Only edges with >= 3 co-occurrences are shown to keep
the graph readable.

**Interactions:**
- Clicking a node highlights its neighborhood and shows a list of papers with
  that tag
- Category toggles let users show/hide applications, tools, or data tags. A
  domain expert hides tools to see which application domains cluster together.
  A TDA researcher hides applications to see which methods co-occur.

**Data flow:**
- Precomputed at index time during `reindex.py`
- Stored as `database/cooccurrence.json`
- The `/explore` route loads this file and passes it to the template
- D3.js (loaded from CDN) renders the graph client-side
- An `/api/tag-cooccurrence` endpoint serves the raw JSON for programmatic use

**Expected scale:** ~50-100 nodes, ~200-400 edges at current dataset size.

### 1.2 Statistics Dashboard (`/stats`)

A page showing:
- Papers per year (bar chart via Chart.js from CDN)
- Top 20 tags by frequency (horizontal bar chart)
- Top 20 authors by paper count (table)
- Application domain distribution (pie/donut chart)
- Total papers, total software entries, total unique authors

All computed server-side from existing indexed data. Chart.js renders charts.
HTML tables as fallback for no-JS users.

### 1.3 Related Papers

For each paper displayed in search results, a collapsible "Related papers"
section showing 3-5 similar papers. Similarity = Jaccard index on tag sets.

- Precomputed during reindexing
- Stored as `database/similarity.json` (~50KB)
- Loaded into memory at app startup
- Displayed via a `<details>` element on each search result card

### 1.4 Timeline View (`/timeline`)

Papers grouped by year, colored by primary application domain. Server-rendered
HTML (year headings with paper lists). Optionally enhanced with a Chart.js
stacked bar chart showing domain distribution over time.

Answers "when did TDA in neuroscience take off?" without requiring a search
query.

---

## Section 2: Contributor Experience

### 2.1 Web Submission Form (`/submit`)

Replaces the Google Form with a structured, guided submission flow. Key idea:
enforce tag consistency at entry time by offering existing tags.

**Fields:**

| Field | Input type | Notes |
|-------|-----------|-------|
| Title | Text | Required |
| Authors | Text (comma-separated) | Required |
| Year | Number | Required |
| DOI or URL | Text | At least one required |
| Abstract | Textarea | Optional but encouraged |
| Entry type | Radio: paper / software | Required |
| Application tags (cat 1) | Autocomplete multi-select from tag index | At least one required |
| Tool tags (cat 2) | Autocomplete multi-select from tag index | At least one required |
| Data tags (cat 3) | Autocomplete multi-select from tag index | At least one required |
| Flavour | Optional radio: innovate / confirm / neither | Optional |
| Code URL | Text | Optional |
| Data URL | Text | Optional |
| Video URL | Text | Optional |

**Tag autocomplete:** Each tag category field queries the existing tag index and
suggests matches as the user types. Contributors can type new tags, but these
get flagged for review.

**On submit:**
1. Validates required fields and tag structure (hierarchical colon format, at
   least one per category)
2. Stores the submission as a JSON file in a `submissions/` directory (gitignored)
3. Optionally sends a notification email to donut@topology.rocks

A maintainer reviews and decides whether to add to Zotero. Preserves the
curation model while reducing back-and-forth on tag formatting.

No authentication needed. Spam risk is low given the academic niche.

### 2.2 CLI Tag Validator

A script `python -m donut.validate_tags` that checks all indexed entries for:

- Missing tag categories (every paper should have at least one in each of
  categories 1, 2, 3)
- Near-duplicate tags using Jaro-Winkler similarity (extending existing
  `analyse_tags.py` logic)
- Tags that appear only once (potential typos or overly specific tags)
- Malformed hierarchical tags (missing parent in "foo:bar:baz" when "foo:bar"
  doesn't exist)

Outputs a report to stdout. Can be run standalone or as part of the reindexing
pipeline.

### 2.3 Tag Similarity Alerts During Reindexing

When `reindex.py` runs, after indexing, automatically run the tag similarity
check and print warnings for new near-duplicates. Catches inconsistencies
early before they propagate.

---

## Section 3: Researcher Productivity

### 3.1 Result Sorting

Sort controls on search results and browse pages:
- **Relevance** -- default for search (current Xapian behavior)
- **Newest first** -- default for `/papers` and `/software`
- **Oldest first**

Implementation: Store `year` as a Xapian value slot (slot 0) during indexing.
Use `enquire.set_sort_by_value_then_relevance()` for year-based sorting. Sort
controls rendered as links above the result list.

Requires one-time reindex after deploying.

### 3.2 Pagination

25 results per page:
- Search results: Xapian's native `get_mset(offset, limit)`
- Browse pages: paginated postlist iteration

Page controls: "Previous / Page N of M / Next" links below results. Query
parameters preserved across pages.

### 3.3 Bulk BibTeX Export

"Export all results as BibTeX" link on search result pages. Downloads a single
`.bib` file with all matching papers. Uses existing `BibTexWriter` infrastructure.

### 3.4 Faceted Search

After a search, show a collapsible refinement panel **above** results (not a
sidebar -- preserves the 80ch layout). Contains:

- Application tags with counts (top 10)
- Tool tags with counts (top 10)
- Data tags with counts (top 10)
- Year buckets (2024-2025, 2021-2023, 2018-2020, pre-2018)
- Type (paper vs software)

Each filter appends to the current query. Computed server-side by scanning the
result set.

---

## Section 4: Architecture

### 4.1 New Files

| File | Purpose |
|------|---------|
| `donut/similarity.py` | Jaccard similarity for related papers |
| `donut/analysis.py` | Tag co-occurrence, statistics aggregation |
| `donut/validate_tags.py` | CLI tag validator |
| `donut/templates/explore.html` | D3.js tag co-occurrence graph |
| `donut/templates/stats.html` | Statistics dashboard with Chart.js |
| `donut/templates/timeline.html` | Timeline view |
| `donut/templates/submit.html` | Submission form |
| `donut/templates/facets.html` | Faceted search partial |
| `database/cooccurrence.json` | Precomputed co-occurrence data |
| `database/similarity.json` | Precomputed related-papers data |

### 4.2 Modified Files

| File | Changes |
|------|---------|
| `donut/__init__.py` | New routes: `/explore`, `/stats`, `/timeline`, `/submit`, `/export-all`, `/api/tag-cooccurrence`. Modified: `/` (sorting, pagination, facets), `/papers`, `/software` (sorting, pagination) |
| `donut/database.py` | Year value slot, pagination params, facet computation |
| `donut/reindex.py` | Post-index: compute similarity + co-occurrence, run tag validation warnings |
| `donut/templates/base.html` | Updated nav, add Submit link |
| `donut/templates/index.html` | Sort controls, pagination, bulk export, facets include, related papers |
| `donut/static/style.css` | Pagination, facet, sort control, submission form styles |

### 4.3 External Dependencies

- **D3.js** (CDN) -- tag co-occurrence graph only
- **Chart.js** (CDN) -- stats dashboard and timeline charts
- No new Python dependencies

### 4.4 Updated Navigation

```
Home | Papers | Software | Explore | Timeline | Stats | Tags | FAQ | Contributors | Submit
```

"Submit" visually distinct (right-aligned or styled as a button).

### 4.5 Implementation Order

| Step | Feature | Dependencies |
|------|---------|-------------|
| 1 | Sorting + Pagination | None (foundation) |
| 2 | Statistics Dashboard | None |
| 3 | Related Papers | Reindex with value slots (step 1) |
| 4 | Tag Co-occurrence Explorer | `analysis.py` |
| 5 | Timeline View | Similar infrastructure to stats |
| 6 | Faceted Search | Pagination (step 1) |
| 7 | Bulk Export | None |
| 8 | CLI Tag Validator | Independent of web |
| 9 | Web Submission Form | Tag index for autocomplete |
| 10 | Tag Similarity Alerts | Validator logic (step 8) |

**Release groups:**
- Release 1: Steps 1-2
- Release 2: Steps 3-5
- Release 3: Steps 6-7
- Release 4: Steps 8-10
