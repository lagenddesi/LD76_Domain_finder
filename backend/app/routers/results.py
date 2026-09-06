from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import authenticated_client
from ..models import DomainResult, ScanHistory
from ..schemas import DomainResultResponse, ScanHistoryResponse
from ..services.persistence import domain_result_to_dict


router = APIRouter(
    prefix="/api",
    tags=["results"],
    dependencies=[Depends(authenticated_client)],
)


@router.get(
    "/results",
    response_model=list[DomainResultResponse],
)
def get_results(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=500),
    min_score: float = Query(default=0, ge=0, le=100),
):
    results = db.scalars(
        select(DomainResult)
        .where(DomainResult.python_score >= min_score)
        .order_by(
            desc(DomainResult.python_score),
            desc(DomainResult.last_scan),
        )
        .limit(limit)
    ).all()

    return [
        domain_result_to_dict(result)
        for result in results
    ]


@router.get(
    "/results/{domain}",
    response_model=DomainResultResponse,
)
def get_result(
    domain: str,
    db: Session = Depends(get_db),
):
    normalized_domain = domain.strip().lower()

    result = db.scalar(
        select(DomainResult).where(
            DomainResult.domain == normalized_domain
        )
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Domain result not found.",
        )

    return domain_result_to_dict(result)


@router.get(
    "/history",
    response_model=list[ScanHistoryResponse],
)
def get_history(
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
):
    history = db.scalars(
        select(ScanHistory)
        .order_by(desc(ScanHistory.started_at))
        .limit(limit)
    ).all()

    return history
