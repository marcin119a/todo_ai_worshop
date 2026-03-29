"""Tests for Epic 3: Deadlines and due date management.

BDD scenarios for:
  - US-3.1: Set due_date when creating/updating a task
  - US-3.2: Filter overdue tasks (GET /tasks/?overdue=true)
  - US-3.3: AI receives due_date and raises priority for near deadlines
  - US-3.4: GET /tasks/upcoming?days=7 for tasks due in the next week
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.models import Priority, Status, Task, User
from app.services.ai_priority_service import MockAIPriorityService, _PRIORITY_CACHE


@pytest.fixture(autouse=True)
def clear_priority_cache():
    """Clear the shared priority cache before each test."""
    _PRIORITY_CACHE.clear()
    yield
    _PRIORITY_CACHE.clear()


# ─────────────────────────────────────────────────────────────────────────────
# US-3.1 — Setting due_date on create and update
# ─────────────────────────────────────────────────────────────────────────────


def test_create_task_with_due_date(client: TestClient) -> None:
    """Scenario: Creating a task with a due date."""
    due = (date.today() + timedelta(days=10)).isoformat()
    response = client.post("/tasks/", json={"title": "Zrób raport", "due_date": due})

    assert response.status_code == 201
    data = response.json()
    assert data["due_date"] == due


def test_create_task_without_due_date(client: TestClient) -> None:
    """due_date is optional — omitting it returns null."""
    response = client.post("/tasks/", json={"title": "Zadanie bez terminu"})

    assert response.status_code == 201
    assert response.json()["due_date"] is None


def test_update_task_sets_due_date(client: TestClient) -> None:
    """Scenario: Updating a task to add a due date."""
    create = client.post("/tasks/", json={"title": "Aktualizacja terminu"})
    task_id = create.json()["id"]

    due = (date.today() + timedelta(days=5)).isoformat()
    response = client.patch(f"/tasks/{task_id}", json={"due_date": due})

    assert response.status_code == 200
    assert response.json()["due_date"] == due


def test_update_task_clears_due_date(client: TestClient) -> None:
    """Scenario: Clearing due_date by setting it to null."""
    due = (date.today() + timedelta(days=5)).isoformat()
    create = client.post("/tasks/", json={"title": "Zadanie", "due_date": due})
    task_id = create.json()["id"]

    response = client.patch(f"/tasks/{task_id}", json={"due_date": None})

    assert response.status_code == 200
    assert response.json()["due_date"] is None


# ─────────────────────────────────────────────────────────────────────────────
# US-3.2 — Filter overdue tasks
# ─────────────────────────────────────────────────────────────────────────────


def test_filter_overdue_returns_only_past_due_tasks(client: TestClient) -> None:
    """Scenario: GET /tasks/?overdue=true returns only tasks past their due_date."""
    past = (date.today() - timedelta(days=1)).isoformat()
    future = (date.today() + timedelta(days=5)).isoformat()

    client.post("/tasks/", json={"title": "Przeterminowane", "due_date": past})
    client.post("/tasks/", json={"title": "Nieprzeterminowane", "due_date": future})
    client.post("/tasks/", json={"title": "Bez terminu"})

    response = client.get("/tasks/?overdue=true")

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "Przeterminowane" in titles
    assert "Nieprzeterminowane" not in titles
    assert "Bez terminu" not in titles


def test_filter_overdue_excludes_done_tasks(client: TestClient) -> None:
    """Scenario: Overdue filter skips completed tasks."""
    past = (date.today() - timedelta(days=2)).isoformat()

    created = client.post("/tasks/", json={"title": "Zrobione", "due_date": past})
    task_id = created.json()["id"]
    client.patch(f"/tasks/{task_id}", json={"status": "done"})

    response = client.get("/tasks/?overdue=true")

    titles = [t["title"] for t in response.json()]
    assert "Zrobione" not in titles


def test_filter_overdue_false_returns_all(client: TestClient) -> None:
    """Without overdue filter, all tasks are returned."""
    past = (date.today() - timedelta(days=1)).isoformat()
    client.post("/tasks/", json={"title": "Stare", "due_date": past})
    client.post("/tasks/", json={"title": "Nowe"})

    response = client.get("/tasks/")

    assert response.status_code == 200
    assert len(response.json()) == 2


def test_admin_all_overdue_filter_returns_only_overdue_tasks(
    admin_client: TestClient,
    test_db: Session,
    test_user: User,
) -> None:
    """Admin GET /tasks/admin/all?overdue=true must return only overdue tasks.

    Regression: admin_get_all_tasks() accepted TaskListParams (including overdue)
    but did not pass overdue=params.overdue to service.get_tasks(), so the filter
    was silently ignored and all tasks were returned.
    """
    today = date.today()
    test_db.add(Task(
        title="Overdue Task",
        priority=Priority.MEDIUM,
        status=Status.TODO,
        due_date=today - timedelta(days=3),
        owner_id=test_user.id,
    ))
    test_db.add(Task(
        title="Future Task",
        priority=Priority.MEDIUM,
        status=Status.TODO,
        due_date=today + timedelta(days=7),
        owner_id=test_user.id,
    ))
    test_db.commit()

    response = admin_client.get("/tasks/admin/all?overdue=true")

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "Overdue Task" in titles
    assert "Future Task" not in titles


def test_admin_all_overdue_filter_excludes_done_tasks(
    admin_client: TestClient,
    test_db: Session,
    test_user: User,
) -> None:
    """Admin overdue filter must not return tasks with status=done."""
    today = date.today()
    test_db.add(Task(
        title="Done Overdue Task",
        priority=Priority.MEDIUM,
        status=Status.DONE,
        due_date=today - timedelta(days=2),
        owner_id=test_user.id,
    ))
    test_db.add(Task(
        title="Pending Overdue Task",
        priority=Priority.MEDIUM,
        status=Status.TODO,
        due_date=today - timedelta(days=2),
        owner_id=test_user.id,
    ))
    test_db.commit()

    response = admin_client.get("/tasks/admin/all?overdue=true")

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "Pending Overdue Task" in titles
    assert "Done Overdue Task" not in titles


def test_admin_all_without_overdue_filter_returns_all_tasks(
    admin_client: TestClient,
    test_db: Session,
    test_user: User,
) -> None:
    """Without ?overdue=true, admin endpoint returns all tasks regardless of due_date."""
    today = date.today()
    test_db.add(Task(
        title="Overdue Task",
        priority=Priority.MEDIUM,
        status=Status.TODO,
        due_date=today - timedelta(days=3),
        owner_id=test_user.id,
    ))
    test_db.add(Task(
        title="Future Task",
        priority=Priority.MEDIUM,
        status=Status.TODO,
        due_date=today + timedelta(days=7),
        owner_id=test_user.id,
    ))
    test_db.commit()

    response = admin_client.get("/tasks/admin/all")

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "Overdue Task" in titles
    assert "Future Task" in titles


# ─────────────────────────────────────────────────────────────────────────────
# US-3.3 — AI receives due_date and raises priority for near deadlines
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ai_boosts_priority_for_overdue_task() -> None:
    """Scenario: AI suggests HIGH for a task already past its due date."""
    svc = MockAIPriorityService()
    past = date.today() - timedelta(days=1)

    priority, reason = await svc.suggest_priority("Cokolwiek", None, due_date=past)

    assert priority.value == "high"
    assert reason is not None
    assert "przeterminowane" in reason.lower() or "termin" in reason.lower()


@pytest.mark.asyncio
async def test_ai_boosts_priority_for_task_due_today() -> None:
    """Scenario: AI suggests HIGH for a task due today."""
    svc = MockAIPriorityService()

    priority, reason = await svc.suggest_priority("Raport", None, due_date=date.today())

    assert priority.value == "high"
    assert reason is not None


@pytest.mark.asyncio
async def test_ai_boosts_priority_for_task_due_in_3_days() -> None:
    """Scenario: AI suggests HIGH for a task due within 3 days."""
    svc = MockAIPriorityService()
    soon = date.today() + timedelta(days=2)

    priority, _ = await svc.suggest_priority("Projekt", None, due_date=soon)

    assert priority.value == "high"


@pytest.mark.asyncio
async def test_ai_does_not_boost_priority_for_distant_due_date() -> None:
    """Scenario: AI does not raise priority for a task due in 14 days."""
    svc = MockAIPriorityService()
    distant = date.today() + timedelta(days=14)

    priority, _ = await svc.suggest_priority("Projekt długoterminowy", None, due_date=distant)

    assert priority.value != "high"


def test_create_task_with_ai_and_near_due_date_sets_high_priority(client: TestClient) -> None:
    """Scenario: Creating a task with use_ai_priority=true and due in 1 day → HIGH."""
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    response = client.post(
        "/tasks/?use_ai_priority=true",
        json={"title": "Pilne zadanie", "due_date": tomorrow},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == "high"
    assert data["ai_override"] is True


def test_reanalyze_preserves_due_date_based_high_priority(client: TestClient) -> None:
    """Reanalysis must pass due_date to AI so deadline-based HIGH priority is kept.

    Regression: reanalyze_priority() called suggest_priority(title, description)
    without due_date, so an overdue task was downgraded to MEDIUM after reanalysis.
    """
    past_due = (date.today() - timedelta(days=5)).isoformat()

    task_resp = client.post(
        "/tasks/?use_ai_priority=true",
        json={
            "title": "Monthly report",
            "description": "Compile financial data",
            "priority": "medium",
            "due_date": past_due,
        },
    )
    assert task_resp.status_code == 201
    task = task_resp.json()
    assert task["priority"] == Priority.HIGH.value, "Setup: overdue task should be HIGH"

    reanalyze_resp = client.post(f"/tasks/{task['id']}/reanalyze-priority")

    assert reanalyze_resp.status_code == 200
    assert reanalyze_resp.json()["priority"] == Priority.HIGH.value, (
        "Reanalysis must preserve HIGH priority for overdue task"
    )


# ─────────────────────────────────────────────────────────────────────────────
# US-3.4 — GET /tasks/upcoming?days=7
# ─────────────────────────────────────────────────────────────────────────────


def test_upcoming_returns_tasks_due_within_window(client: TestClient) -> None:
    """Scenario: /tasks/upcoming?days=7 returns tasks due in the next 7 days."""
    in_3_days = (date.today() + timedelta(days=3)).isoformat()
    in_10_days = (date.today() + timedelta(days=10)).isoformat()
    past = (date.today() - timedelta(days=1)).isoformat()

    client.post("/tasks/", json={"title": "W tym tygodniu", "due_date": in_3_days})
    client.post("/tasks/", json={"title": "Za ponad tydzień", "due_date": in_10_days})
    client.post("/tasks/", json={"title": "Przeterminowane", "due_date": past})
    client.post("/tasks/", json={"title": "Bez terminu"})

    response = client.get("/tasks/upcoming?days=7")

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "W tym tygodniu" in titles
    assert "Za ponad tydzień" not in titles
    assert "Przeterminowane" not in titles
    assert "Bez terminu" not in titles


def test_upcoming_excludes_done_tasks(client: TestClient) -> None:
    """Scenario: /tasks/upcoming excludes completed tasks."""
    soon = (date.today() + timedelta(days=2)).isoformat()

    created = client.post("/tasks/", json={"title": "Ukończone", "due_date": soon})
    task_id = created.json()["id"]
    client.patch(f"/tasks/{task_id}", json={"status": "done"})

    response = client.get("/tasks/upcoming?days=7")

    titles = [t["title"] for t in response.json()]
    assert "Ukończone" not in titles


def test_upcoming_custom_days_parameter(client: TestClient) -> None:
    """Scenario: days parameter controls the look-ahead window."""
    in_15_days = (date.today() + timedelta(days=15)).isoformat()

    client.post("/tasks/", json={"title": "Za 15 dni", "due_date": in_15_days})

    assert len(client.get("/tasks/upcoming?days=7").json()) == 0
    assert len(client.get("/tasks/upcoming?days=30").json()) == 1


def test_upcoming_default_days_is_7(client: TestClient) -> None:
    """Default window is 7 days when days param is omitted."""
    in_5_days = (date.today() + timedelta(days=5)).isoformat()
    client.post("/tasks/", json={"title": "W oknie domyślnym", "due_date": in_5_days})

    response = client.get("/tasks/upcoming")

    assert response.status_code == 200
    titles = [t["title"] for t in response.json()]
    assert "W oknie domyślnym" in titles
