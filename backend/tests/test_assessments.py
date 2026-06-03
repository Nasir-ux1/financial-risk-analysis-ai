import json
import pytest

def test_create_assessment_without_company(client, analyst_headers):
    response = client.post(
        "/api/assessments/",
        json={
            "query": "Assess current inflation thresholds under Basel guidelines.",
            "prompt_variant": "COT"
        },
        headers=analyst_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert "assessment_text" in data
    assert data["prompt_variant"] == "COT"
    assert data["confidence_score"] > 0
    assert "judge_accuracy" in data
    assert data["judge_accuracy"] > 0

def test_create_assessment_with_company(client, analyst_headers):
    # 1. Create company first
    comp_res = client.post(
        "/api/companies/",
        json={
            "name": "TeslaTech",
            "ticker": "TST",
            "industry": "Automotive",
            "financial_summary": {
                "total_assets": 100000.0,
                "total_liabilities": 50000.0,
                "current_assets": 30000.0,
                "current_liabilities": 20000.0,
                "retained_earnings": 10000.0,
                "ebit": 5000.0,
                "revenue": 120000.0,
                "market_equity": 50000.0,
                "interest_expense": 2000.0
            }
        },
        headers=analyst_headers
    )
    company_id = comp_res.json()["id"]

    # 2. Assess company
    response = client.post(
        "/api/assessments/",
        json={
            "company_id": company_id,
            "query": "Should we issue a $10k credit line based on leverage requirements?",
            "prompt_variant": "COT"
        },
        headers=analyst_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["company_id"] == company_id
    assert "assessment_text" in data

def test_compare_prompts(client, analyst_headers):
    response = client.post(
        "/api/assessments/compare",
        json={
            "query": "Perform credit analysis evaluation."
        },
        headers=analyst_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "query" in data
    assert len(data["results"]) == 3  # ZERO_SHOT, FEW_SHOT, COT
    for result in data["results"]:
        assert result["prompt_variant"] in ["ZERO_SHOT", "FEW_SHOT", "COT"]
        assert result["judge_accuracy"] > 0
        assert result["judge_completeness"] > 0

def test_upload_financial_statement(client, analyst_headers):
    file_content = {
        "company_name": "SkyFreight Systems",
        "ticker": "SFS",
        "industry": "Logistics",
        "total_assets": 150000.0,
        "total_liabilities": 80000.0,
        "current_assets": 40000.0,
        "current_liabilities": 30000.0,
        "retained_earnings": 20000.0,
        "ebit": 12000.0,
        "revenue": 200000.0,
        "market_equity": 70000.0,
        "interest_expense": 4000.0
    }
    
    file_payload = json.dumps(file_content)
    files = {"file": ("statement.json", file_payload, "application/json")}
    
    response = client.post(
        "/api/assessments/upload-statement",
        files=files,
        headers=analyst_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "Successfully parsed" in data["message"]
    assert data["company_name"] == "SkyFreight Systems"
    assert data["ratios"]["current_ratio"] == 1.33  # 40000 / 30000
    assert data["ratios"]["debt_to_equity"] == 1.14  # 80000 / 70000
