import json
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
    save_domain_results,
    update_scan_history,
)


class ScanManager:
    """Manage background full and targeted scanner jobs."""

    SCAN_TIMEOUT_SECONDS = 60 * 60
    PYTHON_CANDIDATE_THRESHOLD = 60

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
            self._ensure_not_running()

            scan_id = self._create_history()
            self._running_scan_id = scan_id

            thread = threading.Thread(
                target=self._run_full_scan,
                args=(scan_id,),
                daemon=True,
                name=f"ld76-scan-{scan_id}",
            )
            thread.start()

            return scan_id

    def start_rescan(self, domain: str) -> int:
        with self._lock:
            self._ensure_not_running()

            scan_id = self._create_history()
            self._running_scan_id = scan_id

            thread = threading.Thread(
                target=self._run_targeted_scan,
                args=(scan_id, domain),
                daemon=True,
                name=f"ld76-rescan-{scan_id}",
            )
            thread.start()

            return scan_id

    def _ensure_not_running(self) -> None:
        if self._running_scan_id is not None:
            raise RuntimeError(
                f"Scan {self._running_scan_id} is already running."
            )

    def _create_history(self) -> int:
        db = SessionLocal()

        try:
            history = create_scan_history(db)
            return history.id
        finally:
            db.close()

    def _run_full_scan(self, scan_id: int) -> None:
        self._run_scanner(
            scan_id=scan_id,
            command_type="full",
        )

    def _run_targeted_scan(
        self,
        scan_id: int,
        domain: str,
    ) -> None:
        self._run_scanner(
            scan_id=scan_id,
            command_type="targeted",
            domain=domain,
        )

    def _run_scanner(
        self,
        *,
        scan_id: int,
        command_type: str,
        domain: str | None = None,
    ) -> None:
        try:
            project_root = self._project_root()

            if command_type == "targeted":
                if not domain:
                    raise ValueError(
                        "Targeted scan requires a domain."
                    )

                script_path = (
                    project_root
                    / "scanner"
                    / "rescan.py"
                )
            else:
                script_path = self._resolve_script_path()

            if not script_path.is_file():
                raise FileNotFoundError(
                    f"Scanner script not found: {script_path}"
                )

            command = [
                sys.executable,
                str(script_path),
            ]

            if command_type == "targeted":
                command.append(domain)

            process = subprocess.run(
                command,
                cwd=str(project_root),
                env=os.environ.copy(),
                capture_output=True,
                text=True,
                timeout=self.SCAN_TIMEOUT_SECONDS,
                check=False,
            )

            if process.returncode != 0:
                error = (
                    process.stderr.strip()
                    or process.stdout.strip()
                    or (
                        "Scanner exited with code "
                        f"{process.returncode}."
                    )
                )

                self._finish_scan(
                    scan_id,
                    status="failed",
                    error_message=error[-4000:],
                )
                return

            sync_info = self._sync_results(
                scan_id=scan_id,
                command_type=command_type,
                domain=domain,
            )

            self._finish_scan(
                scan_id,
                status="completed",
            )

            print(
                "[ScanManager] Scan completed:",
                sync_info,
            )

        except subprocess.TimeoutExpired:
            self._finish_scan(
                scan_id,
                status="failed",
                error_message=(
                    "Scanner timed out after "
                    "60 minutes."
                ),
            )

        except Exception as exc:
            self._finish_scan(
                scan_id,
                status="failed",
                error_message=str(exc)[-4000:],
            )

    def _sync_results(
        self,
        *,
        scan_id: int,
        command_type: str,
        domain: str | None,
    ) -> dict[str, int]:
        results_file = (
            self._project_root()
            / "data"
            / "results.json"
        )

        if not results_file.is_file():
            return self._empty_sync_info()

        try:
            with results_file.open(
                "r",
                encoding="utf-8",
            ) as file:
                results = json.load(file)

        except (OSError, json.JSONDecodeError):
            return self._empty_sync_info()

        if not isinstance(results, list):
            return self._empty_sync_info()

        if command_type == "targeted":
            normalized = (
                str(domain or "")
                .strip()
                .lower()
            )

            sync_results = [
                result
                for result in results
                if isinstance(result, dict)
                and str(
                    result.get("domain", "")
                ).strip().lower() == normalized
            ]

            domains_discovered = 1
            domains_scanned = (
                1 if sync_results else 0
            )

        else:
            sync_results = [
                result
                for result in results
                if isinstance(result, dict)
            ]

            domains_discovered = len(sync_results)
            domains_scanned = len(sync_results)

        candidates_found = sum(
            1
            for result in sync_results
            if self._python_score(result)
            >= self.PYTHON_CANDIDATE_THRESHOLD
        )

        db = SessionLocal()

        try:
            saved = save_domain_results(
                db,
                sync_results,
            )

            update_scan_history(
                db,
                scan_id,
                domains_discovered=domains_discovered,
                domains_scanned=domains_scanned,
                candidates_found=candidates_found,
                status="running",
            )

        finally:
            db.close()

        return {
            "saved": saved,
            "discovered": domains_discovered,
            "scanned": domains_scanned,
            "candidates": candidates_found,
        }

    @staticmethod
    def _python_score(
        result: dict[str, Any],
    ) -> float:
        value = result.get(
            "python_score",
            result.get("score", 0),
        )

        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _empty_sync_info() -> dict[str, int]:
        return {
            "saved": 0,
            "discovered": 0,
            "scanned": 0,
            "candidates": 0,
        }

    def _finish_scan(
        self,
        scan_id: int,
        *,
        status: str,
        error_message: str | None = None,
    ) -> None:
        try:
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

        finally:
            with self._lock:
                if self._running_scan_id == scan_id:
                    self._running_scan_id = None

    @staticmethod
    def _project_root() -> Path:
        # backend/app/services
        # -> backend/app
        # -> backend
        # -> repository root
        return Path(__file__).resolve().parents[3]

    def _resolve_script_path(self) -> Path:
        configured = Path(SCANNER_SCRIPT)

        if configured.is_absolute():
            return configured.resolve()

        return (
            self._project_root() / configured
        ).resolve()

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "running": (
                    self._running_scan_id is not None
                ),
                "scan_id": self._running_scan_id,
            }


scan_manager = ScanManager()
