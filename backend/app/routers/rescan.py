from fastapi import APIRouter, Depends, HTTPException, Request

from ..dependencies import authenticated_client
from ..rate_limit import limiter
from ..schemas import RescanResponse
from ..services.scan_manager import scan_manager


router = APIRouter(
    prefix="/api",
    tags=["rescan"],
    dependencies=[Depends(authenticated_client)],
)


@router.post(
    "/rescan/{domain}",
    response_model=RescanResponse,
)
@limiter.limit("10/hour")
def rescan_domain(
    request: Request,
    domain: str,
):
    normalized_domain = domain.strip().lower()

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

    try:
        from scanner.scanner import normalize_domain

        normalized_domain = normalize_domain(
            normalized_domain
        )

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Scanner is unavailable.",
        )

    if not normalized_domain:
        raise HTTPException(
            status_code=400,
            detail="Invalid domain.",
        )

    if scan_manager.is_running():
        raise HTTPException(
            status_code=409,
            detail="Another scan is already running.",
        )

    try:
        scan_id = scan_manager.start_rescan(
            normalized_domain
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to start domain rescan.",
        )

    return RescanResponse(
        scan_id=scan_id,
        status="running",
        domain=normalized_domain,
        message=(
            "Domain rescan started successfully."
        ),
    )
