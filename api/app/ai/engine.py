"""Replaceable inference contract. No detector/model is configured yet."""
from typing import Protocol
from pydantic import AwareDatetime, BaseModel, Field
from typing import Literal
from app.ai.preparation import PreparedConnection


class Finding(BaseModel):
    connection_ids: list[int] = Field(min_length=1, max_length=500)
    timestamp: AwareDatetime
    attack_type: str = Field(min_length=1, max_length=64)
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    description: str = Field(min_length=1)
    mitre_technique: str | None = Field(default=None, max_length=64)


class AnalysisEngine(Protocol):
    name: str
    version: str | None
    configured: bool

    def analyze_batch(self, connections: tuple[PreparedConnection, ...]) -> list[Finding]: ...


class UnconfiguredDetector:
    name = "not_configured"
    version = None
    configured = False

    def analyze_batch(self, connections: tuple[PreparedConnection, ...]) -> list[Finding]:
        # Preparation succeeds, but an empty result here is NOT a safety verdict.
        return []


analysis_engine: AnalysisEngine = UnconfiguredDetector()
