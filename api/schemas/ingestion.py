from pydantic import BaseModel
from typing import Optional


class ParsedSite(BaseModel):
    configuration: str
    network_type: str
    electrical_type: str
    direction_id: int
    estimated_consumption: float
    site_count: int = 1


class IngestionResult(BaseModel):
    status: str
    total_rows: int
    total_sites: int
    sites: list[dict]
    message: str
