"""Tests for task API endpoints."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.db.models import Priority, Status, Task


def test_create_task(client: TestClient) -> None:
    """Test creating a new task."""
    task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "medium",
        "status": "todo",
    }

    response = client.post("/tasks/", json=task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["description"] == task_data["description"]
    assert data["priority"] == task_data["priority"]
    assert data["status"] == task_data["status"]
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_task_with_ai_priority(client: TestClient) -> None:
    """Test creating a task with AI-based priority suggestion."""
    task_data = {
        "title": "Urgent production incident",
        "description": "This is critical and must be fixed ASAP",
        "status": "todo",
    }

    response = client.post("/tasks/?use_ai_priority=true", json=task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["status"] == task_data["status"]
    # MockAIPriorityService should classify this as high priority
    assert data["priority"] == Priority.HIGH.value
    assert data["priority_reason"] is not None
    assert "Wysoki priorytet" in data["priority_reason"] or "urgent" in data["priority_reason"].lower()
    assert "słowa kluczowe" in data["priority_reason"] or "keywords" in data["priority_reason"].lower()


def test_analyze_priority_endpoint(client: TestClient) -> None:
    """Test standalone priority analysis endpoint."""
    payload = {
        "title": "Fix critical bug in production",
        "description": "Users cannot log in, urgent fix needed",
    }

    response = client.post("/tasks/priority/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == Priority.HIGH.value
    assert data["priority_reason"] is not None
    assert len(data["priority_reason"]) > 0
    # Verify the reason contains meaningful explanation
    assert "Wysoki priorytet" in data["priority_reason"] or "urgent" in data["priority_reason"].lower()


def test_get_task(client: TestClient, test_db: Session) -> None:
    """Test getting a task by ID."""
    # Create a task directly in the database
    task = Task(
        title="Test Task",
        description="Test description",
        priority=Priority.MEDIUM,
        status=Status.TODO,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["title"] == task.title


def test_get_task_not_found(client: TestClient) -> None:
    """Test getting a non-existent task."""
    response = client.get("/tasks/999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_all_tasks(client: TestClient, test_db: Session) -> None:
    """Test getting all tasks."""
    # Create multiple tasks
    tasks = [
        Task(title=f"Task {i}", priority=Priority.MEDIUM, status=Status.TODO)
        for i in range(3)
    ]
    for task in tasks:
        test_db.add(task)
    test_db.commit()

    response = client.get("/tasks/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 3


def test_get_tasks_filtered_by_status(client: TestClient, test_db: Session) -> None:
    """Test getting tasks filtered by status."""
    # Create tasks with different statuses
    todo_task = Task(title="Todo Task", status=Status.TODO)
    done_task = Task(title="Done Task", status=Status.DONE)
    test_db.add(todo_task)
    test_db.add(done_task)
    test_db.commit()

    response = client.get("/tasks/?status=done")

    assert response.status_code == 200
    data = response.json()
    assert all(task["status"] == "done" for task in data)


def test_update_task(client: TestClient, test_db: Session) -> None:
    """Test updating a task."""
    # Create a task
    task = Task(
        title="Original Title",
        description="Original description",
        priority=Priority.LOW,
        status=Status.TODO,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    update_data = {
        "title": "Updated Title",
        "status": "done",
    }

    response = client.patch(f"/tasks/{task.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["status"] == update_data["status"]


def test_delete_task(client: TestClient, test_db: Session) -> None:
    """Test deleting a task."""
    # Create a task
    task = Task(title="Task to Delete", priority=Priority.MEDIUM, status=Status.TODO)
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    response = client.delete(f"/tasks/{task.id}")

    assert response.status_code == 204

    # Verify task is deleted
    get_response = client.get(f"/tasks/{task.id}")
    assert get_response.status_code == 404


def test_delete_task_not_found(client: TestClient) -> None:
    """Test deleting a non-existent task."""
    response = client.delete("/tasks/999")

    assert response.status_code == 404


def test_get_task_with_priority_reason(client: TestClient, test_db: Session) -> None:
    """Test getting a task that has priority_reason set."""
    task = Task(
        title="Test Task with Reason",
        description="Test description",
        priority=Priority.HIGH,
        priority_reason="Wysoki priorytet: zadanie zawiera słowa kluczowe 'pilne', 'deadline'",
        status=Status.TODO,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    response = client.get(f"/tasks/{task.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["priority_reason"] == task.priority_reason
    assert "Wysoki priorytet" in data["priority_reason"]


def test_get_all_tasks_includes_priority_reason(client: TestClient, test_db: Session) -> None:
    """Test that all tasks in list include priority_reason field."""
    task1 = Task(
        title="Task 1",
        priority=Priority.HIGH,
        priority_reason="High priority reason",
        status=Status.TODO,
    )
    task2 = Task(
        title="Task 2",
        priority=Priority.MEDIUM,
        priority_reason=None,
        status=Status.TODO,
    )
    test_db.add(task1)
    test_db.add(task2)
    test_db.commit()

    response = client.get("/tasks/")

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2
    
    # Find our tasks
    task1_data = next((t for t in data if t["id"] == task1.id), None)
    task2_data = next((t for t in data if t["id"] == task2.id), None)
    
    assert task1_data is not None
    assert task2_data is not None
    assert "priority_reason" in task1_data
    assert "priority_reason" in task2_data
    assert task1_data["priority_reason"] == "High priority reason"
    assert task2_data["priority_reason"] is None


def test_update_task_priority_reason(client: TestClient, test_db: Session) -> None:
    """Test updating a task's priority_reason."""
    task = Task(
        title="Original Task",
        priority=Priority.MEDIUM,
        priority_reason="Original reason",
        status=Status.TODO,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    update_data = {
        "priority_reason": "Updated: zadanie zostało przeanalizowane ponownie i wymaga pilnej uwagi",
    }

    response = client.patch(f"/tasks/{task.id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["priority_reason"] == update_data["priority_reason"]


def test_create_task_without_ai_has_priority_reason(client: TestClient) -> None:
    """Test that tasks created without AI still have priority_reason set."""
    task_data = {
        "title": "Regular Task",
        "description": "No AI used",
        "priority": "medium",
        "status": "todo",
    }

    response = client.post("/tasks/", json=task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["priority"] == "medium"  # User-provided priority is preserved
    assert data["priority_reason"] is not None  # But priority_reason is still generated
    assert len(data["priority_reason"]) > 0


def test_create_task_exam_overrides_medium_priority_to_high(client: TestClient) -> None:
    """Creating exam task with body priority=medium should still result in high priority."""
    task_data = {
        "title": "Mam bardzo wazny jutro egzamin,",
        "description": "Mam bardzo ważne jutro egzamin",
        "priority": "medium",
        "status": "todo",
    }

    response = client.post("/tasks/", json=task_data)

    assert response.status_code == 201
    data = response.json()
    # Even though user sent 'medium', AI should detect important exam and override to 'high'
    assert data["priority"] == Priority.HIGH.value
    assert data["priority_reason"] is not None
    assert "egzamin" in (data["priority_reason"] or "").lower()


def test_priority_reason_format_contains_key_factors(client: TestClient) -> None:
    """Test that priority reasons contain key factors or keywords."""
    test_cases = [
        {
            "title": "Urgent task with deadline",
            "description": "Must be done ASAP",
            "expected_priority": Priority.HIGH,
        },
        {
            "title": "Low priority optional task",
            "description": "Can be done later",
            "expected_priority": Priority.LOW,
        },
        {
            "title": "Regular daily task",
            "description": "Normal work item",
            "expected_priority": Priority.MEDIUM,
        },
    ]

    for case in test_cases:
        response = client.post(
            "/tasks/priority/analyze",
            json={"title": case["title"], "description": case["description"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == case["expected_priority"].value
        assert data["priority_reason"] is not None
        assert len(data["priority_reason"]) > 10  # Should be meaningful explanation


def test_priority_for_important_exam_is_high(client: TestClient) -> None:
    """Task about very important exam tomorrow should be high priority."""
    payload = {
        "title": "Jutro mam bardzo wazny egzamiN!!!",
        "description": "musze sie przygotowac jutro na egzamin",
    }

    response = client.post("/tasks/priority/analyze", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == Priority.HIGH.value
    assert data["priority_reason"] is not None
    assert "egzamin" in data["priority_reason"].lower()


def test_reanalyze_task_priority(client: TestClient, test_db: Session) -> None:
    """Test re-analyzing priority for an existing task."""
    task = Task(
        title="Regular task",
        description="Normal work",
        priority=Priority.MEDIUM,
        priority_reason="Original reason",
        status=Status.TODO,
    )
    test_db.add(task)
    test_db.commit()
    test_db.refresh(task)

    response = client.post(f"/tasks/{task.id}/reanalyze-priority")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == task.id
    assert data["priority_reason"] is not None
    assert data["priority_reason"] != "Original reason"  # Should be updated
    assert len(data["priority_reason"]) > 10  # Should be meaningful


def test_reanalyze_task_priority_not_found(client: TestClient) -> None:
    """Test re-analyzing priority for a non-existent task."""
    response = client.post("/tasks/999/reanalyze-priority")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

