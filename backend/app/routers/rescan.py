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
    normalized_domain = domain.strip().lower()

    if not normalized_domain:
        raise HTTPException(
            status_code=400,
            detail="Domain is required.",
        )

    if len(normalized_domain) > 253:
        raise HTTPException(
            status_code=400,
            detail="Invalid domain length.",
        )

    if scan_manager.is_running():
        raise HTTPException(
            status_code=409,
            detail=(
                f"Scan {scan_manager.running_scan_id()} is already running."
            ),
        )

    return {
        "status": "accepted",
        "domain": normalized_domain,
        "message": (
            "Single-domain rescan request accepted. "
            "Targeted scanner support will execute this request."
        ),
    }
