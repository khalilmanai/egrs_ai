from pydantic import BaseModel, Field
from typing import Optional


class NewSiteInput(BaseModel):
    configuration: str = Field(..., description="Terminal, Nodal, or Agreg")
    network_type: str = Field(..., description="4G or 5G")
    electrical_type: str = Field(default="BT", description="BT or MT")
    direction_id: int
    estimated_consumption: float = Field(default=5000, description="Estimated annual kWh")
    site_count: int = Field(default=1, ge=1, description="Number of sites")
    commissioning_date: Optional[str] = None


class ReportRequest(BaseModel):
    report_type: str = Field(default="budget_forecast")
    target_year: int = Field(default=2027)
    new_sites: Optional[list[NewSiteInput]] = None
    site_name: Optional[str] = None
    user_prompt: Optional[str] = None
    enterprise: bool = Field(default=False, description="Enable enterprise intelligence mode with health scores, alerts, anomalies, and charts")


class ReportResponse(BaseModel):
    job_id: str
    status: str
    message: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    progress: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None
