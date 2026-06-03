import pytest

def test_create_company_no_financials(client, analyst_headers):
    response = client.post(
        "/api/companies/",
        json={"name": "AeroTech", "ticker": "ART", "industry": "Aerospace"},
        headers=analyst_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "AeroTech"
    assert data["ticker"] == "ART"

def test_create_company_with_financials(client, analyst_headers):
    financial_data = {
        "total_assets": 10000000.0,
        "total_liabilities": 4000000.0,
        "current_assets": 3000000.0,
        "current_liabilities": 2000000.0,
        "retained_earnings": 2000000.0,
        "ebit": 1000000.0,
        "revenue": 12000000.0,
        "market_equity": 6000000.0,
        "interest_expense": 200000.0
    }
    
    response = client.post(
        "/api/companies/",
        json={
            "name": "TeslaTech",
            "ticker": "TST",
            "industry": "Automotive",
            "financial_summary": financial_data
        },
        headers=analyst_headers
    )
    assert response.status_code == 201
    company_data = response.json()
    company_id = company_data["id"]

    # Verify risk profile calculations
    profile_response = client.get(f"/api/companies/{company_id}/risk-profile", headers=analyst_headers)
    assert profile_response.status_code == 200
    profile_data = profile_response.json()
    
    # current_ratio = current_assets / current_liabilities = 3M / 2M = 1.5
    assert profile_data["current_ratio"] == 1.5
    # debt_to_equity = total_liabs / equity = 4M / 6M = 0.67
    assert profile_data["debt_to_equity"] == 0.67
    # interest_coverage = ebit / interest_expense = 1M / 200K = 5.0
    assert profile_data["interest_coverage"] == 5.0
    # altman_z = 1.2A + 1.4B + 3.3C + 0.6D + 0.99E
    # A = WC/Assets = 1M/10M = 0.1
    # B = RE/Assets = 2M/10M = 0.2
    # C = EBIT/Assets = 1M/10M = 0.1
    # D = Equity/Liabs = 6M/4M = 1.5
    # E = Sales/Assets = 12M/10M = 1.2
    # Altman Z = 1.2(0.1) + 1.4(0.2) + 3.3(0.1) + 0.6(1.5) + 0.99(1.2) = 0.12 + 0.28 + 0.33 + 0.9 + 1.188 = 2.82
    assert profile_data["altman_z_score"] == 2.82
    assert profile_data["risk_rating"] in ["LOW", "MEDIUM", "HIGH"]

def test_get_companies(client, analyst_headers):
    # Create two companies
    client.post("/api/companies/", json={"name": "C1", "ticker": "C1", "industry": "I"}, headers=analyst_headers)
    client.post("/api/companies/", json={"name": "C2", "ticker": "C2", "industry": "I"}, headers=analyst_headers)

    response = client.get("/api/companies/", headers=analyst_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2

def test_get_company_not_found(client, analyst_headers):
    response = client.get("/api/companies/999", headers=analyst_headers)
    assert response.status_code == 404
