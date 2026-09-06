import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from ..config import SCANNER_SCRIPT
from ..database import SessionLocal
from .persistence import (
    create_scan_history,
    update_scan_history,
)


class ScanManager:
    """Manage background scanner jobs for the API."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._running_scan_id: int | None = None

    def is_running(self) -> bool:
        with self._lock:
            return self._running_scan_id is not None

    def running_scan_id(self) -> int | None:
        with self._lock:
            return self._running_scan_id

    def start_scan(self) -> int:
        with self._lock:
            if self._running_scan_id is not None:
                raise RuntimeError(
                    f"Scan {self._running_scan_id} is already running."
                )

            db = SessionLocal()

            try:
                history = create_scan_history(db)
                scan_id = history.id
            finally:
                db.close()

            self._running_scan_id = scan_id

            thread = threading.Thread(
                target=self._run_scan,
                args=(scan_id,),
                daemon=True,
                name=f"ld76-scan-{scan_id}",
            )
            thread.start()

            return scan_id

    def _run_scan(self, scan_id: int) -> None:
        db = SessionLocal()

        try:
            update_scan_history(
                db,
                scan_id,
                status="running",
            )
        finally:
            db.close()

        try:
            script_path = self._resolve_script_path()

            if not script_path.is_file():
                raise FileNotFoundError(
                    f"Scanner script not found: {script_path}"
                )

            env = os.environ.copy()

            process = subprocess.run(
                [sys.executable, str(script_path)],
                cwd=str(self._project_root()),
                env=env,
                capture_output=True,
                text=True,
                timeout=60 * 60,
                check=False,
            )

            if process.returncode != 0:
                error = (
                    process.stderr.strip()
                    or process.stdout.strip()
                    or f"Scanner exited with code {process.returncode}."
                )

                self._finish_scan(
                    scan_id,
                    status="failed",
                    error_message=error[-4000:],
                )
                return

            self._finish_scan(
                scan_id,
                status="completed",
            )

        except subprocess.TimeoutExpired:
            self._finish_scan(
                scan_id,
                status="failed",
                error_message="Scanner timed out after 60 minutes.",
            )

        except Exception as exc:
            self._finish_scan(
                scan_id,
                status="failed",
                error_message=str(exc)[-4000:],
            )

    def _finish_scan(
        self,
        scan_id: int,
        *,
        status: str,
        error_message: str | None = None,
    ) -> None:
        db = SessionLocal()

        try:
            update_scan_history(
                db,
                scan_id,
                status=status,
                error_message=error_message,
                finished=True,
            )
        finally:
            db.close()

        with self._lock:
            if self._running_scan_id == scan_id:
                self._running_scan_id = None

    @staticmethod
    def _project_root() -> Path:
        # backend/app/services -> backend/app -> backend -> project root
        return Path(__file__).resolve().parents[3]

    def _resolve_script_path(self) -> Path:
        configured = Path(SCANNER_SCRIPT)

        if configured.is_absolute():
            return configured.resolve()

        return (self._project_root() / configured).resolve()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": self._running_scan_id is not None,
                "scan_id": self._running_scan_id,
            }


scan_manager = ScanManager()
