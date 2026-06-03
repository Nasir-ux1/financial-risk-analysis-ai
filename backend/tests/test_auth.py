import pytest

def test_signup(client):
    response = client.post(
        "/api/auth/signup",
        json={"email": "new_user@riskai.com", "password": "securepassword", "role": "ANALYST"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new_user@riskai.com"
    assert data["role"] == "ANALYST"
    assert "id" in data

def test_signup_existing_email(client):
    # Already seeded in conftest: test_analyst@riskai.com
    response = client.post(
        "/api/auth/signup",
        json={"email": "test_analyst@riskai.com", "password": "password123", "role": "ANALYST"}
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_login_json(client):
    response = client.post(
        "/api/auth/login/json",
        json={"email": "test_analyst@riskai.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["role"] == "ANALYST"
    assert data["email"] == "test_analyst@riskai.com"

def test_login_form(client):
    response = client.post(
        "/api/auth/login",
        data={"username": "test_analyst@riskai.com", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data

def test_login_invalid_credentials(client):
    response = client.post(
        "/api/auth/login/json",
        json={"email": "test_analyst@riskai.com", "password": "wrong_password"}
    )
    assert response.status_code == 401

def test_read_me(client, analyst_headers):
    response = client.get("/api/auth/me", headers=analyst_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "test_analyst@riskai.com"
