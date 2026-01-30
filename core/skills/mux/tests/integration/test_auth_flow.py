#!/usr/bin/env python3
"""Integration tests for auth flow with A2A server."""
import os
import sys
import tempfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

# Import auth module
a2a_dir = Path(__file__).parent.parent.parent / "a2a"
auth_path = a2a_dir / "auth.py"

spec_auth = spec_from_file_location("auth", auth_path)
if spec_auth is None or spec_auth.loader is None:
    raise ImportError(f"Cannot load auth from {auth_path}")
auth = module_from_spec(spec_auth)
sys.modules["auth"] = auth
spec_auth.loader.exec_module(auth)

# Import symbols
verify_token = auth.verify_token
get_valid_tokens = auth.get_valid_tokens


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


def test_dev_mode_auth_flow(result: TestResult):
    """Test dev mode authentication flow end-to-end."""
    test_name = "test_dev_mode_auth_flow"
    try:
        # Setup: Enable dev mode
        os.environ["AGENTIC_MUX_DEV_MODE"] = "true"
        os.environ.pop("A2A_BEARER_TOKENS", None)

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Simulate server request with any token
                auth_header = "Bearer dev-test-token-12345"
                authenticated = verify_token(auth_header)

                assert authenticated is True, "Dev mode should allow any token"

                # Simulate multiple requests with different tokens
                for token in ["token1", "token2", "random-string"]:
                    auth_header = f"Bearer {token}"
                    assert verify_token(auth_header) is True

                result.add_pass(test_name)
            finally:
                os.chdir(old_cwd)
                os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_production_mode_auth_flow(result: TestResult):
    """Test production mode authentication flow end-to-end."""
    test_name = "test_production_mode_auth_flow"
    try:
        # Setup: Production mode with configured token
        os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
        os.environ["A2A_BEARER_TOKENS"] = "prod-token-abc123,prod-token-xyz789"

        try:
            # Valid token should authenticate
            assert verify_token("Bearer prod-token-abc123") is True
            assert verify_token("Bearer prod-token-xyz789") is True

            # Invalid token should fail
            assert verify_token("Bearer invalid-token") is False
            assert verify_token("Bearer ") is False
            assert verify_token("prod-token-abc123") is False  # Missing Bearer prefix

            result.add_pass(test_name)
        finally:
            os.environ.pop("A2A_BEARER_TOKENS", None)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_production_mode_no_tokens_rejects(result: TestResult):
    """Test production mode rejects all requests when no tokens configured."""
    test_name = "test_production_mode_no_tokens_rejects"
    try:
        # Setup: Production mode, no tokens
        os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
        os.environ.pop("A2A_BEARER_TOKENS", None)

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # All requests should be rejected
                assert verify_token("Bearer any-token") is False
                assert verify_token("Bearer secure-looking-token") is False

                result.add_pass(test_name)
            finally:
                os.chdir(old_cwd)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_auth_flow_with_file_based_tokens(result: TestResult):
    """Test authentication flow with file-based token configuration."""
    test_name = "test_auth_flow_with_file_based_tokens"
    try:
        os.environ.pop("AGENTIC_MUX_DEV_MODE", None)
        os.environ.pop("A2A_BEARER_TOKENS", None)

        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create .a2a/tokens file
                a2a_dir = Path(tmpdir) / ".a2a"
                a2a_dir.mkdir()
                tokens_file = a2a_dir / "tokens"
                tokens_file.write_text("file-token-001\nfile-token-002\n")

                # Valid tokens from file should authenticate
                assert verify_token("Bearer file-token-001") is True
                assert verify_token("Bearer file-token-002") is True

                # Invalid token should fail
                assert verify_token("Bearer wrong-token") is False

                result.add_pass(test_name)
            finally:
                os.chdir(old_cwd)
    except Exception as e:
        result.add_fail(test_name, str(e))


if __name__ == "__main__":
    result = TestResult()
    test_dev_mode_auth_flow(result)
    test_production_mode_auth_flow(result)
    test_production_mode_no_tokens_rejects(result)
    test_auth_flow_with_file_based_tokens(result)

    success = result.summary()
    sys.exit(0 if success else 1)
