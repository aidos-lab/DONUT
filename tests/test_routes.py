"""Tests for Flask routes."""


def test_index_get(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Database of Original" in response.data


def test_search_post(client):
    response = client.post("/", data={"query": "homology"})
    assert response.status_code == 200


def test_search_get_with_query(client):
    response = client.get("/?q=homology")
    assert response.status_code == 200


def test_search_with_sort(client):
    response = client.get("/?q=homology&sort=year_desc")
    assert response.status_code == 200


def test_papers_page(client):
    response = client.get("/papers")
    assert response.status_code == 200


def test_papers_page_2(client):
    response = client.get("/papers?page=2")
    assert response.status_code == 200


def test_software_page(client):
    response = client.get("/software")
    assert response.status_code == 200


def test_tags_page(client):
    response = client.get("/tags")
    assert response.status_code == 200


def test_faq_page(client):
    response = client.get("/faq")
    assert response.status_code == 200


def test_random_page(client):
    response = client.post("/random")
    assert response.status_code == 200


def test_export(client):
    response = client.get("/export/1")
    assert response.status_code == 200
    assert response.content_type == "application/x-bibtex"


def test_export_all(client):
    response = client.get("/export-all?q=homology")
    assert response.status_code == 200
    assert response.content_type == "application/x-bibtex"


def test_export_all_no_query(client):
    response = client.get("/export-all")
    assert response.status_code == 200
    assert response.content_type == "application/x-bibtex"


def test_stats_page(client):
    response = client.get("/stats")
    assert response.status_code == 200
    assert b"Database Statistics" in response.data


def test_explore_page(client):
    response = client.get("/explore")
    assert response.status_code == 200
    assert b"Tag Co-occurrence" in response.data


def test_api_tag_cooccurrence(client):
    response = client.get("/api/tag-cooccurrence")
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)


def test_timeline_page(client):
    response = client.get("/timeline")
    assert response.status_code == 200
    assert b"Timeline" in response.data


def test_submit_page_get(client):
    response = client.get("/submit")
    assert response.status_code == 200
    assert b"Submit a Paper" in response.data


def test_submit_page_post_missing_fields(client):
    response = client.post("/submit", data={
        "title": "",
        "authors": "",
        "year": "",
    })
    assert response.status_code == 200
    assert b"required" in response.data.lower()


def test_submit_page_post_valid(client):
    response = client.post("/submit", data={
        "title": "Test Paper",
        "authors": "Test Author",
        "year": "2024",
        "doi": "10.1234/test",
        "entry_type": "article",
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Thank you" in response.data


def test_contributors_page(client):
    response = client.get("/contributors")
    assert response.status_code == 200
