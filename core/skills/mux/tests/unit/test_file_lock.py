#!/usr/bin/env python3
"""Unit tests for file locking utilities."""
import tempfile
import time
from multiprocessing import Process, Queue
from pathlib import Path

# Import will fail initially (RED phase)
from core.skills.mux.lib.file_lock import FileLock, atomic_write, LockTimeout


def _hold_lock_helper(lock_path: Path, q: Queue):
    """Process helper that holds lock for 2 seconds."""
    try:
        lock = FileLock(lock_path, timeout=5)
        lock.acquire()
        q.put("acquired")
        time.sleep(2)
        lock.release()
        q.put("released")
    except Exception as e:
        q.put(f"error:{e}")


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


def test_file_lock_basic(result: TestResult):
    """Test basic lock acquisition and release."""
    test_name = "test_file_lock_basic"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / "test.lock"

            # Acquire lock
            lock = FileLock(lock_file)
            lock.acquire()

            # Verify lock file exists
            assert lock_file.exists(), "Lock file should exist"

            # Release lock
            lock.release()

            # Lock file can remain (that's OK)
            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_file_lock_exclusive(result: TestResult):
    """Test that two processes cannot hold lock simultaneously."""
    test_name = "test_file_lock_exclusive"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / "test.lock"
            queue = Queue()

            # Start process that holds lock
            p = Process(target=_hold_lock_helper, args=(lock_file, queue))
            p.start()

            # Wait for first process to acquire lock
            msg = queue.get(timeout=2)
            assert msg == "acquired", f"First process should acquire lock, got: {msg}"

            # Try to acquire lock from main process (should timeout)
            lock = FileLock(lock_file, timeout=0.5)
            try:
                lock.acquire()
                result.add_fail(test_name, "Second lock should timeout")
                lock.release()
            except LockTimeout:
                # Expected timeout
                pass

            # Wait for first process to release
            p.join(timeout=5)

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_file_lock_timeout(result: TestResult):
    """Test that lock acquisition times out correctly."""
    test_name = "test_file_lock_timeout"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / "test.lock"

            # Acquire lock
            lock1 = FileLock(lock_file, timeout=5)
            lock1.acquire()

            # Try to acquire same lock with short timeout
            lock2 = FileLock(lock_file, timeout=0.5)
            start = time.time()
            try:
                lock2.acquire()
                result.add_fail(test_name, "Should have timed out")
                lock2.release()
            except LockTimeout:
                elapsed = time.time() - start
                # Should timeout around 0.5s (allow 0.2s margin)
                if elapsed < 0.3 or elapsed > 0.7:
                    result.add_fail(test_name, f"Timeout took {elapsed}s, expected ~0.5s")
                else:
                    result.add_pass(test_name)
            finally:
                lock1.release()
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_file_lock_context_manager(result: TestResult):
    """Test context manager automatic cleanup."""
    test_name = "test_file_lock_context_manager"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            lock_file = Path(tmpdir) / "test.lock"

            # Use context manager
            with FileLock(lock_file, timeout=5):
                pass  # Lock held here

            # Lock should be released, we should be able to acquire it
            lock = FileLock(lock_file, timeout=0.5)
            lock.acquire()
            lock.release()

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_atomic_write_basic(result: TestResult):
    """Test atomic write creates file correctly."""
    test_name = "test_atomic_write_basic"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "test.txt"
            content = "test content\n"

            atomic_write(target_file, content)

            # Verify file exists and has correct content
            assert target_file.exists(), "File should exist"
            assert target_file.read_text() == content, "Content should match"

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


def test_atomic_write_concurrent(result: TestResult):
    """Test atomic write safety under concurrent access."""
    test_name = "test_atomic_write_concurrent"
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            target_file = Path(tmpdir) / "test.txt"

            # Write multiple times concurrently
            processes = []
            for i in range(5):
                content = f"content-{i}\n"
                p = Process(target=atomic_write, args=(target_file, content))
                p.start()
                processes.append(p)

            for p in processes:
                p.join(timeout=2)

            # File should exist and contain valid content from one of the writes
            assert target_file.exists(), "File should exist"
            final_content = target_file.read_text()
            assert final_content.startswith("content-"), "Content should be valid"

            result.add_pass(test_name)
    except Exception as e:
        result.add_fail(test_name, str(e))


if __name__ == "__main__":
    result = TestResult()

    test_file_lock_basic(result)
    test_file_lock_exclusive(result)
    test_file_lock_timeout(result)
    test_file_lock_context_manager(result)
    test_atomic_write_basic(result)
    test_atomic_write_concurrent(result)

    success = result.summary()
    exit(0 if success else 1)
