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
    assert data["priority_reason"] == "Contains urgent keywords"


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
    assert data["priority_reason"] == "Contains urgent keywords"


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

