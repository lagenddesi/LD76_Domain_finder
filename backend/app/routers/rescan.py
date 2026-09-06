from fastapi import APIRouter, Depends, HTTPException

from ..dependencies import authenticated_client
from ..services.scan_manager import scan_manager


router = APIRouter(
    prefix="/api",
    tags=["rescan"],
    dependencies=[Depends(authenticated_client)],
)


@router.post("/rescan/{domain}")
def rescan_domain(domain: str):
    domain = domain.strip()

    if not domain:
        raise HTTPException(
            status_code=400,
            detail="Domain is required.",
        )

    if len(domain) > 253:
        raise HTTPException(
            status_code=400,
            detail="Invalid domain length.",
        )

    # Reuse the scanner's own normalization/validation logic.
    try:
        from scanner.scanner import normalize_domain

        normalized_domain = normalize_domain(domain)

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Domain validation failed: {exc}",
        ) from exc

    if not normalized_domain:
        raise HTTPException(
            status_code=400,
            detail="Invalid domain. Only .top domains are supported.",
        )

    if scan_manager.is_running():
        raise HTTPException(
            status_code=409,
            detail=(
                f"Scan {scan_manager.running_scan_id()} "
                "is already running."
            ),
        )

    try:
        scan_id = scan_manager.start_rescan(
            normalized_domain
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Unable to start rescan: {exc}",
        ) from exc

    return {
        "status": "started",
        "scan_id": scan_id,
        "domain": normalized_domain,
        "message": (
            "Targeted domain rescan started successfully."
        ),
    }
