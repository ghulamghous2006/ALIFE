"""Single-instance protection for ALIFE."""

import logging
import os
from pathlib import Path
from types import TracebackType

logger = logging.getLogger(__name__)

DEFAULT_LOCK_PATH = Path(__file__).resolve().parent.parent / "data" / "alife.lock"


class InstanceLock:
    """Prevent duplicate ALIFE processes using a PID lock file."""

    def __init__(self, lock_path: Path = DEFAULT_LOCK_PATH) -> None:
        """Initialize the instance lock."""
        self._lock_path = lock_path
        self._acquired = False

    def acquire(self) -> bool:
        """Acquire the lock if no other live ALIFE process holds it.

        Returns:
            True if this process now owns the lock.
        """
        self._lock_path.parent.mkdir(parents=True, exist_ok=True)
        existing_pid = self._read_pid()
        if existing_pid is not None and self._pid_is_running(existing_pid):
            logger.warning("Another ALIFE instance is already running (pid=%s)", existing_pid)
            return False

        self._lock_path.write_text(str(os.getpid()), encoding="utf-8")
        self._acquired = True
        logger.info("Acquired instance lock at %s", self._lock_path)
        return True

    def release(self) -> None:
        """Release the lock if this process owns it."""
        if not self._acquired:
            return
        try:
            current = self._read_pid()
            if current == os.getpid() and self._lock_path.exists():
                self._lock_path.unlink()
        except OSError as exc:
            logger.debug("Could not remove instance lock: %s", exc)
        self._acquired = False

    def _read_pid(self) -> int | None:
        if not self._lock_path.exists():
            return None
        try:
            return int(self._lock_path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def _pid_is_running(self, pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    def __enter__(self) -> "InstanceLock":
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.release()
