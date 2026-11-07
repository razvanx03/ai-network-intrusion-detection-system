from typing import Literal
from pydantic import BaseModel, Field


class SensorFileIssue(BaseModel):
    file: str = Field(min_length=1, max_length=1024)
    code: Literal["corrupt_file", "unreadable_file", "oversized_file", "file_unavailable"]
    offset: int | None = Field(default=None, ge=0)
