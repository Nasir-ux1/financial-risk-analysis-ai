import pytest

def test_create_regulatory_reference_as_admin(client, admin_headers):
    response = client.post(
        "/api/regulatory/",
        json={
            "source": "BASEL_IV",
            "section": "Section 9.1",
            "content": "Specifies additional core liquidity parameters under extreme geopolitical friction environments."
        },
        headers=admin_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source"] == "BASEL_IV"
    assert data["section"] == "Section 9.1"

def test_create_regulatory_reference_as_analyst_forbidden(client, analyst_headers):
    response = client.post(
        "/api/regulatory/",
        json={
            "source": "BASEL_IV",
            "section": "Section 9.1",
            "content": "Unauthorized text insert."
        },
        headers=analyst_headers
    )
    assert response.status_code == 403

def test_list_regulatory_references(client, analyst_headers, admin_headers):
    # Add a reference first
    client.post(
        "/api/regulatory/",
        json={"source": "IFRS_17", "section": "Part A", "content": "Insurance risk specifications."},
        headers=admin_headers
    )

    response = client.get("/api/regulatory/", headers=analyst_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any(ref["source"] == "IFRS_17" for ref in data)

def test_search_regulatory_references(client, analyst_headers, admin_headers):
    # Insert descriptive content
    client.post(
        "/api/regulatory/",
        json={
            "source": "BASEL_III", 
            "section": "LCR Ratio Rules", 
            "content": "Liquidity Coverage Ratio (LCR) mandates a stock of high quality liquid assets."
        },
        headers=admin_headers
    )
    
    # Trigger manually
    client.post("/api/regulatory/reindex", headers=admin_headers)

    # Perform RAG search
    response = client.get("/api/regulatory/search?q=mandates%20liquidity%20coverage", headers=analyst_headers)
    assert response.status_code == 200
    results = response.json()
    assert len(results) >= 1
    # Check that highest scoring matches contain Basel or Liquidity terms
    assert any("liquidity" in r["content"].lower() or "basel" in r["content"].lower() for r in results)
