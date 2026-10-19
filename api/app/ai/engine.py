"""Analysis boundary for the demonstration detector and future AI implementations."""
from typing import Protocol
from app.ai.detector import detector_engine


class AnalysisEngine(Protocol):
    def analyze_batch(self, connections: list[dict]) -> list[dict]: ...


# The current engine is demonstrative: its baseline uses synthetic traffic.
analysis_engine: AnalysisEngine = detector_engine
