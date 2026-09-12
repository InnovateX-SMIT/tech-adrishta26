from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(..., examples=["ok"])
    service: str = Field(..., examples=["RESQ backend"])
    phase: str = Field(..., examples=["phase-1"])


class SystemInfoResponse(BaseModel):
    project: str = Field(..., examples=["RESQ"])
    mode: str = Field(..., examples=["development"])
    mesh_enabled: bool = Field(False, examples=[False])
    encryption_enabled: bool = Field(False, examples=[False])
    phase: int = Field(1, examples=[1])
