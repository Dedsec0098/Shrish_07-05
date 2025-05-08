\
from pydantic import BaseModel
from typing import Optional, List
import datetime

class ReportID(BaseModel):
    report_id: str

class ReportStatus(BaseModel):
    status: str

class ReportResult(BaseModel):
    store_id: str
    uptime_last_hour: float
    uptime_last_day: float
    uptime_last_week: float
    downtime_last_hour: float
    downtime_last_day: float
    downtime_last_week: float

    class Config:
        orm_mode = True

