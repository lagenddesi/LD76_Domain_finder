import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import DomainResult, ScanHistory


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _json_string(value: Any) -> str | None:
    if value is None:
        return None

    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError):
        return None


def _json_value(value: str | None) -> list:
    if not value:
        return []

    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return []

    return parsed if isinstance(parsed, list) else []


def domain_result_to_dict(result: DomainResult) -> dict:
    return {
        "id": result.id,
        "domain": result.domain,
        "first_seen": result.first_seen,
        "last_seen": result.last_seen,
        "last_scan": result.last_scan,
        "status": result.status,
        "python_score": result.python_score,
        "gemini_score": result.gemini_score,
        "gemini_analyzed": result.gemini_analyzed,
        "content_hash": result.content_hash,
        "title": result.title,
        "url": result.url,
        "classification": result.classification,
        "reason": result.reason,
        "evidence": _json_value(result.evidence_json),
        "signals": _json_value(result.signals_json),
    }


def history_to_dict(history: ScanHistory) -> dict:
    return {
        "id": history.id,
        "started_at": history.started_at,
        "finished_at": history.finished_at,
        "status": history.status,
        "domains_discovered": history.domains_discovered,
        "domains_scanned": history.domains_scanned,
        "candidates_found": history.candidates_found,
        "error_message": history.error_message,
    }


def upsert_domain_result(
    db: Session,
    data: dict,
) -> DomainResult:
    domain = str(data.get("domain", "")).strip().lower()

    if not domain:
        raise ValueError("Domain is required.")

    result = db.scalar(
        select(DomainResult).where(
            DomainResult.domain == domain
        )
    )

    now = utc_now()

    if result is None:
        result = DomainResult(
            domain=domain,
            first_seen=now,
        )
        db.add(result)

    result.last_seen = now
    result.last_scan = now

    result.status = str(
        data.get("status", result.status or "unknown")
    )

    result.python_score = float(
        data.get("python_score", 0.0) or 0.0
    )

    gemini_score = data.get("gemini_score")

    if gemini_score is not None:
        result.gemini_score = float(gemini_score)

    if "gemini_analyzed" in data:
        result.gemini_analyzed = bool(
            data.get("gemini_analyzed")
        )

    result.content_hash = data.get(
        "content_hash",
        result.content_hash,
    )

    result.title = data.get(
        "title",
        result.title,
    )

    result.url = data.get(
        "url",
        result.url,
    )

    result.classification = data.get(
        "classification",
        result.classification,
    )

    result.reason = data.get(
        "reason",
        result.reason,
    )

    if "evidence" in data:
        result.evidence_json = _json_string(
            data.get("evidence")
        )

    if "signals" in data:
        result.signals_json = _json_string(
            data.get("signals")
        )

    return result


def save_domain_results(
    db: Session,
    results: list[dict],
) -> int:
    saved = 0

    for data in results:
        try:
            upsert_domain_result(db, data)
            saved += 1
        except (TypeError, ValueError):
            continue

    db.commit()

    return saved


def create_scan_history(
    db: Session,
    domains_discovered: int = 0,
) -> ScanHistory:
    history = ScanHistory(
        started_at=utc_now(),
        status="started",
        domains_discovered=domains_discovered,
    )

    db.add(history)
    db.commit()
    db.refresh(history)

    return history


def update_scan_history(
    db: Session,
    scan_id: int,
    *,
    status: str,
    domains_discovered: int | None = None,
    domains_scanned: int | None = None,
    candidates_found: int | None = None,
    error_message: str | None = None,
    finished: bool = False,
) -> ScanHistory | None:
    history = db.get(ScanHistory, scan_id)

    if history is None:
        return None

    history.status = status

    if domains_discovered is not None:
        history.domains_discovered = domains_discovered

    if domains_scanned is not None:
        history.domains_scanned = domains_scanned

    if candidates_found is not None:
        history.candidates_found = candidates_found

    history.error_message = error_message

    if finished:
        history.finished_at = utc_now()

    db.commit()
    db.refresh(history)

    return history
