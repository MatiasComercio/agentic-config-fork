#!/usr/bin/env python3
"""Integration tests for signal race conditions."""
import subprocess
import tempfile
from multiprocessing import Process
from pathlib import Path


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


def create_signal_process(signal_path: Path, output_path: Path, process_id: int):
    """Process function to create signal file."""
    cmd = [
        "uv", "run",
        "core/skills/mux/tools/signal.py",
        str(signal_path),
        "--path", str(output_path),
        "--status", "success",
    ]
    subprocess.run(cmd, capture_output=True)


def test_signal_concurrent_creation(result: TestResult):
    """Test concurrent signal creation is atomic and race-free."""
    test_name = "test_signal_concurrent_creation"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            signals_dir = tmpdir / ".signals"
            output_file = tmpdir / "output.md"

            # Create output file
            output_file.write_text("test content\n")

            # Create 10 concurrent processes writing to same signal
            processes = []
            for i in range(10):
                signal_file = signals_dir / f"concurrent-{i:03d}.done"
                p = Process(target=create_signal_process, args=(signal_file, output_file, i))
                p.start()
                processes.append(p)

            # Wait for all processes to complete
            for p in processes:
                p.join(timeout=5)

            # Verify all signal files exist and are valid
            for i in range(10):
                signal_file = signals_dir / f"concurrent-{i:03d}.done"
                assert signal_file.exists(), f"Signal file {i} should exist"
                content = signal_file.read_text()
                assert "status: success" in content, f"Signal {i} should have valid content"

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


if __name__ == "__main__":
    result = TestResult()
    test_signal_concurrent_creation(result)
    success = result.summary()
    exit(0 if success else 1)
