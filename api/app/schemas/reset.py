from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    confirmation: Literal["RESET"]


class ResetStatus(BaseModel):
    operation_id: str | None
    pending: bool
