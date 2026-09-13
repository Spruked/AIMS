"""Cross-process exclusive lock for append-only A.I.M.S. ledgers."""

from __future__ import annotations

import os
import time
from pathlib import Path


class LedgerWriterLock:
    """Stdlib-only exclusive lock for Windows and POSIX ledger writers."""

    def __init__(self, path: Path, timeout_seconds: float = 15.0):
        self.path = Path(path)
        self.timeout_seconds = timeout_seconds
        self._handle = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._handle = open(self.path, "a+b")
        self._handle.seek(0, os.SEEK_END)
        if self._handle.tell() == 0:
            self._handle.seek(0)
            self._handle.write(b"0")
            self._handle.flush()
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    self._handle.seek(0)
                    msvcrt.locking(self._handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError:
                if time.monotonic() >= deadline:
                    self._handle.close()
                    self._handle = None
                    raise TimeoutError(f"Timed out waiting for ledger writer lock: {self.path}")
                time.sleep(0.05)

    def __exit__(self, exc_type, exc, traceback):
        if not self._handle:
            return
        try:
            if os.name == "nt":
                import msvcrt
                self._handle.seek(0)
                msvcrt.locking(self._handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._handle.close()
            self._handle = None
