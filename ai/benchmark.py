"""Measure the selected classifier in a fresh inference-only process on real rows."""
import ctypes
from ctypes import wintypes
import json
import os
import platform
import statistics
import sys
import time

from ai.acquire import ROOT, WORK
sys.path.insert(0, str(ROOT / "api"))


def peak_rss_bytes() -> int:
    if os.name == "nt":
        class MemoryCounters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                        ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                        ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        counters = MemoryCounters()
        counters.cb = ctypes.sizeof(counters)
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        memory = ctypes.WinDLL("psapi", use_last_error=True)
        memory.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
        if not memory.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.PeakWorkingSetSize)
    import resource
    size = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(size if platform.system() == "Darwin" else size * 1024)


def main() -> None:
    import numpy as np
    import pandas as pd
    from app.ai.detector import load_detector

    started = time.perf_counter()
    detector = load_detector()
    load_seconds = time.perf_counter() - started
    manifest = json.loads((ROOT / "api/app/ai/deployment.json").read_text())
    rows = pd.read_parquet(WORK / f"runs/{manifest['run_id']}/partitions.parquet")
    rows = rows.loc[rows.partition.eq("test")].head(500)
    from app.ai.features import FEATURE_COLUMNS
    timings = []
    for _ in range(11):
        started = time.perf_counter()
        scores = detector.model.predict_proba(rows.loc[:, FEATURE_COLUMNS])[:, 1]
        timings.append(time.perf_counter() - started)
    report = {"rows": len(rows), "model_load_seconds": load_seconds,
              "median_batch_ms": statistics.median(timings[1:]) * 1000,
              "peak_process_rss_bytes": peak_rss_bytes(), "platform": platform.platform(),
              "notes": "Fresh process includes imports, model and heldout table; CPU timing on this host only.",
              "selected_artifact_bytes": (ROOT / "api/app/ai/models/selected.joblib").stat().st_size,
              "finite_scores": bool(np.isfinite(scores).all())}
    (ROOT / "ai/reports/runtime_resources.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
