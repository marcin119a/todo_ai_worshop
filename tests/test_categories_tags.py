"""Tests for Epic 2: Categories and Tags.

BDD scenarios for:
  - US-2.1: Task categories (CRUD, assignment, deletion cascade)
  - US-2.2: Task tags (add, remove, dedup)
  - US-2.3: Filtering by category and tag
  - US-2.4: AI takes category into account for priority suggestion
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.models import Priority, Status, Task, User
from app.services.ai_priority_service import _PRIORITY_CACHE


@pytest.fixture(autouse=True)
def clear_priority_cache():
    """Clear the shared priority cache before each test."""
    _PRIORITY_CACHE.clear()
    yield
    _PRIORITY_CACHE.clear()


# ─────────────────────────────────────────────────────────────────────────────
# US-2.1 — Categories of tasks
# ─────────────────────────────────────────────────────────────────────────────


def test_create_category(client: TestClient) -> None:
    """Scenario: Creating a new category."""
    response = client.post("/categories/", json={"name": "Praca", "color": "#FF5733"})

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["name"] == "Praca"
    assert data["color"] == "#FF5733"


def test_create_category_without_color(client: TestClient) -> None:
    """Category color is optional."""
    response = client.post("/categories/", json={"name": "Praca"})

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Praca"
    assert "id" in data


def test_create_category_duplicate_name_returns_409(client: TestClient) -> None:
    """Scenario: Tworzenie kategorii o już istniejącej nazwie."""
    client.post("/categories/", json={"name": "Praca"})

    response = client.post("/categories/", json={"name": "Praca"})

    assert response.status_code == 409


def test_assign_task_to_category_at_creation(client: TestClient) -> None:
    """Scenario: Przypisanie zadania do kategorii przy tworzeniu."""
    cat = client.post("/categories/", json={"name": "Praca"}).json()

    response = client.post("/tasks/", json={"title": "Raport", "category_id": cat["id"]})

    assert response.status_code == 201
    data = response.json()
    assert data["category"]["id"] == cat["id"]
    assert data["category"]["name"] == "Praca"


def test_assign_task_to_nonexistent_category_returns_404(client: TestClient) -> None:
    """Scenario: Przypisanie zadania do nieistniejącej kategorii."""
    response = client.post("/tasks/", json={"title": "Raport", "category_id": 999})

    assert response.status_code == 404


def test_change_task_category(client: TestClient) -> None:
    """Scenario: Zmiana kategorii istniejącego zadania."""
    praca = client.post("/categories/", json={"name": "Praca"}).json()
    dom = client.post("/categories/", json={"name": "Dom"}).json()
    task = client.post("/tasks/", json={"title": "Raport", "category_id": praca["id"]}).json()

    response = client.patch(f"/tasks/{task['id']}", json={"category_id": dom["id"]})

    assert response.status_code == 200
    assert response.json()["category"]["name"] == "Dom"


def test_delete_category_nullifies_tasks_category(client: TestClient) -> None:
    """Scenario: Usunięcie kategorii przy istniejących zadaniach."""
    praca = client.post("/categories/", json={"name": "Praca"}).json()
    task_ids = [
        client.post("/tasks/", json={"title": f"Task {i}", "category_id": praca["id"]}).json()["id"]
        for i in range(3)
    ]

    response = client.delete(f"/categories/{praca['id']}")

    assert response.status_code == 200
    for task_id in task_ids:
        task_data = client.get(f"/tasks/{task_id}").json()
        assert task_data["category"] is None


# ─────────────────────────────────────────────────────────────────────────────
# US-2.2 — Tags for tasks
# ─────────────────────────────────────────────────────────────────────────────


def test_add_tags_to_task_at_creation(client: TestClient) -> None:
    """Scenario: Adding tags to a task at creation."""
    response = client.post("/tasks/", json={"title": "Raport", "tags": ["pilne", "Q1"]})

    assert response.status_code == 201
    data = response.json()
    assert "pilne" in data["tags"]
    assert "Q1" in data["tags"]


def test_add_tag_to_existing_task(client: TestClient) -> None:
    """Scenario: Adding a tag to an existing task."""
    task = client.post("/tasks/", json={"title": "Raport"}).json()

    response = client.post(f"/tasks/{task['id']}/tags", json={"name": "pilne"})

    assert response.status_code == 200
    assert "pilne" in response.json()["tags"]


def test_remove_tag_from_task(client: TestClient) -> None:
    """Scenario: Removing a tag from a task."""
    task = client.post("/tasks/", json={"title": "Raport", "tags": ["pilne", "Q1"]}).json()

    response = client.delete(f"/tasks/{task['id']}/tags/pilne")

    assert response.status_code == 200
    data = response.json()
    assert "pilne" not in data["tags"]
    assert "Q1" in data["tags"]


def test_duplicate_tag_appears_only_once(client: TestClient) -> None:
    """Scenario: Adding a duplicate tag to a task."""
    task = client.post("/tasks/", json={"title": "Raport", "tags": ["pilne"]}).json()

    response = client.post(f"/tasks/{task['id']}/tags", json={"name": "pilne"})

    assert response.status_code == 200
    assert response.json()["tags"].count("pilne") == 1


# ─────────────────────────────────────────────────────────────────────────────
# US-2.3 — Filtering tasks by category and tag
# ─────────────────────────────────────────────────────────────────────────────


def test_filter_tasks_by_category(client: TestClient) -> None:
    """Scenario: Filtering tasks by category."""
    praca = client.post("/categories/", json={"name": "Praca"}).json()
    dom = client.post("/categories/", json={"name": "Dom"}).json()
    client.post("/tasks/", json={"title": "Raport", "category_id": praca["id"]})
    client.post("/tasks/", json={"title": "Zakupy", "category_id": dom["id"]})

    response = client.get(f"/tasks/?category_id={praca['id']}")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all(t["category"]["id"] == praca["id"] for t in data)


def test_filter_tasks_by_tag(client: TestClient) -> None:
    """Scenario: Filtering tasks by tag."""
    client.post("/tasks/", json={"title": "Raport", "tags": ["pilne"]})
    client.post("/tasks/", json={"title": "Zakupy", "tags": ["weekend"]})

    response = client.get("/tasks/?tag=pilne")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert all("pilne" in t["tags"] for t in data)


def test_filter_tasks_by_category_and_tag(client: TestClient) -> None:
    """Scenario: Filtering tasks by category and tag simultaneously."""
    praca = client.post("/categories/", json={"name": "Praca"}).json()
    dom = client.post("/categories/", json={"name": "Dom"}).json()
    client.post("/tasks/", json={"title": "Raport", "category_id": praca["id"], "tags": ["pilne"]})
    client.post("/tasks/", json={"title": "Meeting", "category_id": praca["id"], "tags": ["weekend"]})
    client.post("/tasks/", json={"title": "Zakupy", "category_id": dom["id"], "tags": ["pilne"]})

    response = client.get(f"/tasks/?category_id={praca['id']}&tag=pilne")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Raport"


def test_filter_by_nonexistent_category_returns_empty_list(client: TestClient) -> None:
    """Scenario: Filtrowanie bez wyników."""
    response = client.get("/tasks/?category_id=99")

    assert response.status_code == 200
    assert response.json() == []


def test_filter_by_nonexistent_tag_returns_empty_list(client: TestClient) -> None:
    """Scenario: Filtrowanie po nieistniejącym tagu."""
    response = client.get("/tasks/?tag=nieistniejący")

    assert response.status_code == 200
    assert response.json() == []


# ─────────────────────────────────────────────────────────────────────────────
# US-2.4 — AI considers category when suggesting priority
# ─────────────────────────────────────────────────────────────────────────────


def test_ai_raises_priority_for_exams_category(client: TestClient) -> None:
    """Scenario: AI raises the priority of a task in the 'Exams' category."""
    egzaminy = client.post("/categories/", json={"name": "Egzaminy"}).json()

    response = client.post(
        "/tasks/?use_ai_priority=true",
        json={"title": "Nauka", "category_id": egzaminy["id"], "priority": "low"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == Priority.HIGH.value
    assert data["ai_override"] is True


def test_ai_no_priority_change_for_hobby_category(client: TestClient) -> None:
    """Scenario: AI does not change priority for a hobby category."""
    hobby = client.post("/categories/", json={"name": "Hobby"}).json()

    response = client.post(
        "/tasks/?use_ai_priority=true",
        json={"title": "Szydełkowanie", "category_id": hobby["id"], "priority": "low"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == Priority.LOW.value
    assert data["ai_override"] is False


def test_ai_unavailable_priority_unchanged(client: TestClient) -> None:
    """Scenario: AI unavailable — category-based priority ignored, no error.

    When use_ai_priority is not set, user-provided priority is preserved
    (MockAIPriorityService returns MEDIUM for 'Nauka', which does not trigger
    the AUTO-HIGH override, so 'medium' from the body stays).
    """
    cat = client.post("/categories/", json={"name": "Egzaminy"}).json()

    response = client.post(
        "/tasks/",
        json={"title": "Nauka", "category_id": cat["id"], "priority": "medium"},
    )

    assert response.status_code == 201
    assert response.json()["priority"] == Priority.MEDIUM.value


def test_reanalyze_preserves_category_based_high_priority(client: TestClient) -> None:
    """Reanalysis must pass category_name to AI so category-based HIGH is preserved.

    Regression: reanalyze_priority() called suggest_priority(title, description)
    without category_name — a task in "Egzaminy" was downgraded to MEDIUM after
    reanalysis because the category context was lost.
    """
    cat = client.post("/categories/", json={"name": "Egzaminy"}).json()

    task_resp = client.post(
        "/tasks/?use_ai_priority=true",
        json={
            "title": "Prepare study notes",
            "description": "Review lecture materials",
            "priority": "medium",
            "category_id": cat["id"],
        },
    )
    assert task_resp.status_code == 201
    task = task_resp.json()
    assert task["priority"] == Priority.HIGH.value, "Setup: Egzaminy category → HIGH"

    reanalyze_resp = client.post(f"/tasks/{task['id']}/reanalyze-priority")

    assert reanalyze_resp.status_code == 200
    assert reanalyze_resp.json()["priority"] == Priority.HIGH.value, (
        "Reanalysis must preserve HIGH priority set by category context"
    )


def test_reanalyze_sets_ai_override_when_ai_overrides_user_priority(
    client: TestClient,
) -> None:
    """ai_override must be True after reanalysis when AI still overrides user priority.

    Verifies the positive case: task in "Egzaminy" category with user-set MEDIUM
    should keep ai_override=True after reanalysis (AI still returns HIGH).
    """
    cat = client.post("/categories/", json={"name": "Egzaminy"}).json()

    task_resp = client.post(
        "/tasks/?use_ai_priority=true",
        json={
            "title": "Final review session",
            "description": "Go through all topics",
            "priority": "medium",
            "category_id": cat["id"],
        },
    )
    assert task_resp.status_code == 201
    task = task_resp.json()
    assert task["priority"] == Priority.HIGH.value
    assert task["ai_override"] is True

    reanalyze_resp = client.post(f"/tasks/{task['id']}/reanalyze-priority")

    assert reanalyze_resp.status_code == 200
    reanalyzed = reanalyze_resp.json()
    assert reanalyzed["priority"] == Priority.HIGH.value
    assert reanalyzed["ai_override"] is True, (
        "ai_override stays True when AI still overrides user-set MEDIUM to HIGH"
    )
