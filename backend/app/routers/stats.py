from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import authenticated_client
from ..models import DomainResult, ScanHistory
from ..rate_limit import limiter


router = APIRouter(
    prefix="/api",
    tags=["stats"],
    dependencies=[Depends(authenticated_client)],
)


@router.get("/stats")
@limiter.limit("60/minute")
def get_stats(
    request: Request,
    db: Session = Depends(get_db),
):
    total_domains = db.scalar(
        select(func.count(DomainResult.id))
    ) or 0

    active_domains = db.scalar(
        select(func.count(DomainResult.id)).where(
            DomainResult.status == "active"
        )
    ) or 0

    python_candidates = db.scalar(
        select(func.count(DomainResult.id)).where(
            DomainResult.python_score >= 60
        )
    ) or 0

    strong_candidates = db.scalar(
        select(func.count(DomainResult.id)).where(
            DomainResult.python_score >= 80
        )
    ) or 0

    gemini_analyzed = db.scalar(
        select(func.count(DomainResult.id)).where(
            DomainResult.gemini_analyzed.is_(True)
        )
    ) or 0

    completed_scans = db.scalar(
        select(func.count(ScanHistory.id)).where(
            ScanHistory.status == "completed"
        )
    ) or 0

    failed_scans = db.scalar(
        select(func.count(ScanHistory.id)).where(
            ScanHistory.status == "failed"
        )
    ) or 0

    running_scans = db.scalar(
        select(func.count(ScanHistory.id)).where(
            ScanHistory.status == "running"
        )
    ) or 0

    return {
        "domains": {
            "total": total_domains,
            "active": active_domains,
            "python_candidates": python_candidates,
            "strong_candidates": strong_candidates,
            "gemini_analyzed": gemini_analyzed,
        },
        "scans": {
            "completed": completed_scans,
            "failed": failed_scans,
            "running": running_scans,
            "total": (
                completed_scans
                + failed_scans
                + running_scans
            ),
        },
    }
