#!/usr/bin/env python3
"""Integration tests for circuit breaker race conditions under high concurrency."""
import sys
import tempfile
import time
from importlib.util import spec_from_file_location, module_from_spec
from multiprocessing import Process, Queue
from pathlib import Path

# Import circuit_breaker module directly from script
script_path = Path(__file__).parent.parent.parent / "tools" / "circuit-breaker.py"
spec = spec_from_file_location("circuit_breaker", script_path)
if spec is None or spec.loader is None:
    raise ImportError(f"Cannot load circuit_breaker from {script_path}")
circuit_breaker = module_from_spec(spec)
sys.modules["circuit_breaker"] = circuit_breaker
spec.loader.exec_module(circuit_breaker)

# Import needed symbols
CircuitState = circuit_breaker.CircuitState
CircuitStatus = circuit_breaker.CircuitStatus
check_circuit = circuit_breaker.check_circuit
record_success = circuit_breaker.record_success
record_failure = circuit_breaker.record_failure
load_circuit = circuit_breaker.load_circuit
save_circuit = circuit_breaker.save_circuit
FAILURE_THRESHOLD = circuit_breaker.FAILURE_THRESHOLD
RESET_TIMEOUT = circuit_breaker.RESET_TIMEOUT


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


def _check_and_report_helper(session_path: Path, agent: str, q: Queue):
    """Helper for multiprocessing - must be at module level."""
    try:
        allowed = check_circuit(session_path, agent)
        q.put(("ok", allowed))
    except Exception as e:
        q.put(("error", str(e)))


def test_multi_process_check_circuit_race(result: TestResult):
    """Test check_circuit under high concurrency (20 processes)."""
    test_name = "test_multi_process_check_circuit_race"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            agent_type = "test_agent"

            # Setup: OPEN circuit with expired timeout
            status = CircuitStatus(
                state=CircuitState.OPEN,
                failure_count=FAILURE_THRESHOLD,
                last_failure_time=time.time() - RESET_TIMEOUT - 1,
                half_open_successes=0,
            )
            save_circuit(session_dir, agent_type, status)

            queue = Queue()

            # Start 20 concurrent processes
            processes = []
            for _ in range(20):
                p = Process(target=_check_and_report_helper, args=(session_dir, agent_type, queue))
                p.start()
                processes.append(p)

            for p in processes:
                p.join(timeout=3)

            # All should complete successfully
            results = []
            while not queue.empty():
                results.append(queue.get())

            assert len(results) == 20, f"Expected 20 results, got {len(results)}"
            for r in results:
                assert r[0] == "ok", f"Process failed: {r}"

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_multi_process_record_success_race(result: TestResult):
    """Test record_success under high concurrency (10 processes)."""
    test_name = "test_multi_process_record_success_race"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            session_dir = Path(tmpdir)
            agent_type = "test_agent"

            # Setup: CLOSED state
            status = CircuitStatus.default()
            save_circuit(session_dir, agent_type, status)

            # Record 10 concurrent successes
            processes = []
            for _ in range(10):
                p = Process(target=record_success, args=(session_dir, agent_type))
                p.start()
                processes.append(p)

            for p in processes:
                p.join(timeout=3)

            # Should remain CLOSED with failure_count=0
            final_status = load_circuit(session_dir, agent_type)
            assert final_status.state == CircuitState.CLOSED, f"Expected CLOSED, got {final_status.state}"
            assert final_status.failure_count == 0, f"Expected 0 failures, got {final_status.failure_count}"

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


if __name__ == "__main__":
    result = TestResult()

    test_multi_process_check_circuit_race(result)
    test_multi_process_record_success_race(result)

    success = result.summary()
    exit(0 if success else 1)
