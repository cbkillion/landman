from datetime import date
from typing import Optional, List
from pydantic import BaseModel, Field

# ---- Projects ----
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    client_name: Optional[str] = Field(None, max_length=255)
    jurisdiction: Optional[str] = Field(None, max_length=255)

class ProjectOut(BaseModel):
    id: str
    name: str
    client_name: Optional[str] = None
    jurisdiction: Optional[str] = None
    status: str
    created_by: str

    class Config:
        from_attributes = True

# ---- Rows ----
class RunSheetRowCreate(BaseModel):
    row_order: int = Field(..., ge=1)
    instrument: str = Field(..., min_length=1, max_length=255)
    volume: Optional[str] = Field(None, max_length=50)
    page: Optional[str] = Field(None, max_length=50)
    grantor: str = Field(..., min_length=1, max_length=255)
    grantee: str = Field(..., min_length=1, max_length=255)
    exec_date: Optional[date] = None
    filed_date: Optional[date] = None
    legal_description: Optional[str] = None
    notes: Optional[str] = None

class BulkRowsCreate(BaseModel):
    rows: List[RunSheetRowCreate]

class RunSheetRowPatch(BaseModel):
    row_order: Optional[int] = Field(None, ge=1)
    instrument: Optional[str] = Field(None, min_length=1, max_length=255)
    volume: Optional[str] = Field(None, max_length=50)
    page: Optional[str] = Field(None, max_length=50)
    grantor: Optional[str] = Field(None, min_length=1, max_length=255)
    grantee: Optional[str] = Field(None, min_length=1, max_length=255)
    exec_date: Optional[date] = None
    filed_date: Optional[date] = None
    legal_description: Optional[str] = None
    notes: Optional[str] = None
    is_deleted: Optional[bool] = None

class RunSheetRowOut(BaseModel):
    id: str
    project_id: str
    row_order: int
    instrument: str
    volume: Optional[str] = None
    page: Optional[str] = None
    grantor: str
    grantee: str
    exec_date: Optional[date] = None
    filed_date: Optional[date] = None
    legal_description: Optional[str] = None
    notes: Optional[str] = None
    is_deleted: bool

    class Config:
        from_attributes = True
