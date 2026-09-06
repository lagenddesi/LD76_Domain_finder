import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import authenticated_client
from ..models import DomainResult, ScanHistory
from ..rate_limit import limiter
from ..schemas import DomainResultResponse, ScanHistoryResponse


router = APIRouter(
    prefix="/api",
    tags=["results"],
    dependencies=[Depends(authenticated_client)],
)


def _load_json_list(value):
    if not value:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, str):
        try:
            parsed = json.loads(value)

            if isinstance(parsed, list):
                return parsed

        except json.JSONDecodeError:
            pass

    return []


def _result_response(result: DomainResult) -> DomainResultResponse:
    return DomainResultResponse(
        id=result.id,
        domain=result.domain,
        first_seen=result.first_seen,
        last_seen=result.last_seen,
        last_scan=result.last_scan,
        status=result.status,
        python_score=result.python_score,
        gemini_score=result.gemini_score,
        gemini_analyzed=result.gemini_analyzed,
        content_hash=result.content_hash,
        title=result.title,
        url=result.url,
        classification=result.classification,
        reason=result.reason,
        evidence=_load_json_list(result.evidence_json),
        signals=_load_json_list(result.signals_json),
    )


@router.get(
    "/results",
    response_model=list[DomainResultResponse],
)
@limiter.limit("120/minute")
def get_results(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    min_score: float = Query(
        default=0,
        ge=0,
    ),
    min_gemini_score: float | None = Query(
        default=None,
        ge=0,
    ),
    classification: str | None = Query(
        default=None,
        max_length=50,
    ),
    search: str | None = Query(
        default=None,
        max_length=253,
    ),
):
    stmt = select(DomainResult)

    if min_score > 0:
        stmt = stmt.where(
            DomainResult.python_score >= min_score
        )

    if min_gemini_score is not None:
        stmt = stmt.where(
            DomainResult.gemini_score >= min_gemini_score
        )

    if classification:
        classification_value = (
            classification.strip().lower()
        )

        if classification_value:
            stmt = stmt.where(
                DomainResult.classification
                == classification_value
            )

    if search:
        search_value = (
            search.strip().lower()
        )

        if search_value:
            search_pattern = (
                f"%{search_value}%"
            )

            stmt = stmt.where(
                or_(
                    DomainResult.domain.ilike(
                        search_pattern
                    ),
                    DomainResult.title.ilike(
                        search_pattern
                    ),
                )
            )

    stmt = (
        stmt.order_by(
            DomainResult.python_score.desc(),
            DomainResult.gemini_score.desc(),
            DomainResult.last_scan.desc(),
        )
        .limit(limit)
    )

    results = db.scalars(stmt).all()

    return [
        _result_response(result)
        for result in results
    ]


@router.get(
    "/results/{domain}",
    response_model=DomainResultResponse,
)
@limiter.limit("120/minute")
def get_result(
    request: Request,
    domain: str,
    db: Session = Depends(get_db),
):
    normalized_domain = (
        domain.strip().lower()
    )

    if not normalized_domain:
        raise HTTPException(
            status_code=400,
            detail="Domain is required.",
        )

    if len(normalized_domain) > 253:
        raise HTTPException(
            status_code=400,
            detail="Invalid domain.",
        )

    result = db.scalar(
        select(DomainResult).where(
            DomainResult.domain
            == normalized_domain
        )
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Domain result not found.",
        )

    return _result_response(result)


@router.get(
    "/history",
    response_model=list[ScanHistoryResponse],
)
@limiter.limit("60/minute")
def get_history(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
    ),
):
    stmt = (
        select(ScanHistory)
        .order_by(
            ScanHistory.started_at.desc()
        )
        .limit(limit)
    )

    history = db.scalars(stmt).all()

    return [
        ScanHistoryResponse(
            id=item.id,
            started_at=item.started_at,
            finished_at=item.finished_at,
            status=item.status,
            domains_discovered=item.domains_discovered,
            domains_scanned=item.domains_scanned,
            candidates_found=item.candidates_found,
            error_message=item.error_message,
        )
        for item in history
    ]
