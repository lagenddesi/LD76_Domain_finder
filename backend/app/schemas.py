from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DomainResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    domain: str
    first_seen: datetime
    last_seen: datetime
    last_scan: datetime | None = None
    status: str

    python_score: float
    gemini_score: float | None = None
    gemini_analyzed: bool

    content_hash: str | None = None
    title: str | None = None
    url: str | None = None

    classification: str | None = None
    reason: str | None = None

    evidence: list = Field(default_factory=list)
    signals: list = Field(default_factory=list)


class ScanHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    started_at: datetime
    finished_at: datetime | None = None
    status: str

    domains_discovered: int
    domains_scanned: int
    candidates_found: int

    error_message: str | None = None


class ScanStartResponse(BaseModel):
    scan_id: int
    status: str
    message: str


class ScanStatusResponse(BaseModel):
    scan_id: int
    status: str

    domains_discovered: int
    domains_scanned: int
    candidates_found: int

    error_message: str | None = None
