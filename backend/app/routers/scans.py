from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..database import get_db
from ..dependencies import authenticated_client
from ..models import ScanHistory
from ..schemas import ScanStartResponse, ScanStatusResponse
from ..services.scan_manager import scan_manager


limiter = Limiter(key_func=get_remote_address)


router = APIRouter(
    prefix="/api",
    tags=["scans"],
    dependencies=[Depends(authenticated_client)],
)


@router.post(
    "/scan/start",
    response_model=ScanStartResponse,
)
@limiter.limit("3/hour")
def start_scan(request: Request):
    try:
        scan_id = scan_manager.start_scan()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return ScanStartResponse(
        scan_id=scan_id,
        status="started",
        message="Domain scan started successfully.",
    )


@router.get(
    "/scan/status",
    response_model=ScanStatusResponse,
)
@limiter.limit("60/minute")
def get_current_scan_status(
    request: Request,
    db: Session = Depends(get_db),
):
    running_id = scan_manager.running_scan_id()

    if running_id is None:
        latest = db.scalar(
            select(ScanHistory)
            .order_by(ScanHistory.id.desc())
            .limit(1)
        )

        if latest is None:
            return ScanStatusResponse(
                scan_id=0,
                status="idle",
                domains_discovered=0,
                domains_scanned=0,
                candidates_found=0,
            )

        return ScanStatusResponse(
            scan_id=latest.id,
            status=latest.status,
            domains_discovered=latest.domains_discovered,
            domains_scanned=latest.domains_scanned,
            candidates_found=latest.candidates_found,
            error_message=latest.error_message,
        )

    history = db.get(ScanHistory, running_id)

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Scan history record not found.",
        )

    return ScanStatusResponse(
        scan_id=history.id,
        status=history.status,
        domains_discovered=history.domains_discovered,
        domains_scanned=history.domains_scanned,
        candidates_found=history.candidates_found,
        error_message=history.error_message,
    )


@router.get(
    "/scan/status/{scan_id}",
    response_model=ScanStatusResponse,
)
@limiter.limit("60/minute")
def get_scan_status(
    request: Request,
    scan_id: int,
    db: Session = Depends(get_db),
):
    history = db.get(ScanHistory, scan_id)

    if history is None:
        raise HTTPException(
            status_code=404,
            detail="Scan not found.",
        )

    return ScanStatusResponse(
        scan_id=history.id,
        status=history.status,
        domains_discovered=history.domains_discovered,
        domains_scanned=history.domains_scanned,
        candidates_found=history.candidates_found,
        error_message=history.error_message,
    )
