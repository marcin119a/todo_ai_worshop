"""Tests for authentication endpoints."""

import pytest
from fastapi.testclient import TestClient


def test_register_new_user(unauth_client: TestClient) -> None:
    """Successful registration returns 201 with user data (no password)."""
    response = unauth_client.post(
        "/auth/register",
        json={"email": "new@example.com", "password": "secret123"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "new@example.com"
    assert data["is_admin"] is False
    assert "id" in data
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_email(unauth_client: TestClient) -> None:
    """Registering the same email twice returns 400."""
    payload = {"email": "dup@example.com", "password": "pass"}
    unauth_client.post("/auth/register", json=payload)

    response = unauth_client.post("/auth/register", json=payload)

    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


def test_login_success(unauth_client: TestClient) -> None:
    """Valid credentials return a bearer JWT token."""
    unauth_client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "mypassword"},
    )

    response = unauth_client.post(
        "/auth/login",
        data={"username": "login@example.com", "password": "mypassword"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_login_wrong_password(unauth_client: TestClient) -> None:
    """Wrong password returns 401."""
    unauth_client.post(
        "/auth/register",
        json={"email": "wrongpass@example.com", "password": "correct"},
    )

    response = unauth_client.post(
        "/auth/login",
        data={"username": "wrongpass@example.com", "password": "incorrect"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_unknown_email(unauth_client: TestClient) -> None:
    """Login with non-existent email returns 401."""
    response = unauth_client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": "anything"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_token_grants_access(unauth_client: TestClient) -> None:
    """Token returned by /login can be used to access a protected endpoint."""
    unauth_client.post(
        "/auth/register",
        json={"email": "tokenuser@example.com", "password": "pass123"},
    )
    login_resp = unauth_client.post(
        "/auth/login",
        data={"username": "tokenuser@example.com", "password": "pass123"},
    )
    token = login_resp.json()["access_token"]

    response = unauth_client.get(
        "/tasks/",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_protected_endpoint_without_token(unauth_client: TestClient) -> None:
    """Request without token to a protected endpoint returns 401."""
    response = unauth_client.get("/tasks/")

    assert response.status_code == 401
