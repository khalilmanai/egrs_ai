from pydantic import BaseModel
from typing import Any, Optional


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None


class PaginatedResponse(BaseModel):
    data: list[dict]
    total: int
    page: int
    limit: int


class SiteDto(BaseModel):
    site_id: int
    site_code: Optional[str] = None
    site_name: Optional[str] = None
    configuration: Optional[str] = None
    elec_type: Optional[str] = None
    network_type_id: Optional[int] = None
    direction_id: Optional[int] = None
