#!/usr/bin/env python3
"""Unit tests for A2A server module."""
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Import from parent
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "a2a"))

from server import create_app, TaskRequest


class TestResult:
    """Test result tracking."""
    def __init__(self):
        self.passed = []
        self.failed = []

    def add_pass(self, test_name: str):
        self.passed.append(test_name)
        print(f"✓ {test_name}")

    def add_fail(self, test_name: str, error: str):
        self.failed.append((test_name, error))
        print(f"✗ {test_name}: {error}")

    def summary(self):
        total = len(self.passed) + len(self.failed)
        print(f"\n{len(self.passed)}/{total} tests passed")
        if self.failed:
            print("\nFailed tests:")
            for name, error in self.failed:
                print(f"  - {name}: {error}")
        return len(self.failed) == 0


def test_create_app(result: TestResult):
    """Test Flask app creation."""
    test_name = "test_create_app"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            app = create_app(storage_dir)

            assert app is not None
            assert hasattr(app, 'route')

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_task_request_validation(result: TestResult):
    """Test TaskRequest model validation."""
    test_name = "test_task_request_validation"
    try:
        # Valid request
        req = TaskRequest(
            session_id="test-session",
            prompt="Test prompt",
            agent_type="test-agent"
        )
        assert req.session_id == "test-session"
        assert req.prompt == "Test prompt"
        assert req.agent_type == "test-agent"

        # With optional model config
        req_with_config = TaskRequest(
            session_id="test-session",
            prompt="Test prompt",
            agent_type="test-agent",
            model_config={"temperature": 0.7}
        )
        assert req_with_config.model_config == {"temperature": 0.7}

        result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_submit_endpoint_with_auth(result: TestResult):
    """Test /a2a/tasks/submit endpoint with authentication."""
    test_name = "test_submit_endpoint_with_auth"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            app = create_app(storage_dir)
            client = app.test_client()

            # Setup dev mode for testing
            os.environ["AGENTIC_MUX_DEV_MODE"] = "true"

            try:
                # Valid request
                response = client.post(
                    "/a2a/tasks/submit",
                    headers={"Authorization": "Bearer test-token"},
                    json={
                        "session_id": "test-session",
                        "prompt": "Test task",
                        "agent_type": "test-agent"
                    }
                )

                assert response.status_code == 200
                data = json.loads(response.data)
                assert "task_id" in data
                assert data["status"] == "submitted"

                result.add_pass(test_name)
            finally:
                os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_submit_endpoint_no_auth(result: TestResult):
    """Test /a2a/tasks/submit endpoint rejects without auth."""
    test_name = "test_submit_endpoint_no_auth"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            app = create_app(storage_dir)
            client = app.test_client()

            # Production mode (no auth configured)
            os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
            os.environ.pop("A2A_BEARER_TOKENS", None)

            # Request without Authorization header
            response = client.post(
                "/a2a/tasks/submit",
                json={
                    "session_id": "test-session",
                    "prompt": "Test task",
                    "agent_type": "test-agent"
                }
            )

            assert response.status_code == 401

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_get_task_endpoint(result: TestResult):
    """Test /a2a/tasks/<task_id> endpoint."""
    test_name = "test_get_task_endpoint"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            app = create_app(storage_dir)
            client = app.test_client()

            os.environ["AGENTIC_MUX_DEV_MODE"] = "true"

            try:
                # Create a task first
                submit_response = client.post(
                    "/a2a/tasks/submit",
                    headers={"Authorization": "Bearer test-token"},
                    json={
                        "session_id": "test-session",
                        "prompt": "Test task",
                        "agent_type": "test-agent"
                    }
                )
                task_id = json.loads(submit_response.data)["task_id"]

                # Get the task
                get_response = client.get(
                    f"/a2a/tasks/{task_id}",
                    headers={"Authorization": "Bearer test-token"}
                )

                assert get_response.status_code == 200
                data = json.loads(get_response.data)
                assert data["id"] == task_id
                assert data["sessionId"] == "test-session"

                result.add_pass(test_name)
            finally:
                os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_get_task_not_found(result: TestResult):
    """Test /a2a/tasks/<task_id> with non-existent task."""
    test_name = "test_get_task_not_found"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            app = create_app(storage_dir)
            client = app.test_client()

            os.environ["AGENTIC_MUX_DEV_MODE"] = "true"

            try:
                response = client.get(
                    "/a2a/tasks/nonexistent-task-id",
                    headers={"Authorization": "Bearer test-token"}
                )

                assert response.status_code == 404

                result.add_pass(test_name)
            finally:
                os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_cancel_task_endpoint(result: TestResult):
    """Test /a2a/tasks/<task_id>/cancel endpoint."""
    test_name = "test_cancel_task_endpoint"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            storage_dir = Path(tmpdir)
            app = create_app(storage_dir)
            client = app.test_client()

            os.environ["AGENTIC_MUX_DEV_MODE"] = "true"

            try:
                # Create a task
                submit_response = client.post(
                    "/a2a/tasks/submit",
                    headers={"Authorization": "Bearer test-token"},
                    json={
                        "session_id": "test-session",
                        "prompt": "Test task",
                        "agent_type": "test-agent"
                    }
                )
                task_id = json.loads(submit_response.data)["task_id"]

                # Cancel the task
                cancel_response = client.post(
                    f"/a2a/tasks/{task_id}/cancel",
                    headers={"Authorization": "Bearer test-token"}
                )

                assert cancel_response.status_code == 200
                data = json.loads(cancel_response.data)
                assert data["status"]["state"] == "canceled"

                result.add_pass(test_name)
            finally:
                os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
    except Exception as e:
        result.add_fail(test_name, str(e))


if __name__ == "__main__":
    result = TestResult()
    test_create_app(result)
    test_task_request_validation(result)
    test_submit_endpoint_with_auth(result)
    test_submit_endpoint_no_auth(result)
    test_get_task_endpoint(result)
    test_get_task_not_found(result)
    test_cancel_task_endpoint(result)

    success = result.summary()
    sys.exit(0 if success else 1)
