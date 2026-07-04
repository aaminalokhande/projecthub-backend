from pydantic import BaseModel
from typing import Optional
from datetime import date


class ProjectCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: Optional[str] = "active"
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    team_lead_id: Optional[int] = None


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[date] = None
    due_date: Optional[date] = None
    team_lead_id: Optional[int] = None


class ProjectResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    status: Optional[str]
    start_date: Optional[date]
    due_date: Optional[date]
    owner_id: int
    team_lead_id: Optional[int]

    class Config:
        from_attributes = True