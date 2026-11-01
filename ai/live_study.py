"""Read-only sensor collection and frozen-candidate evaluation on labelled VM flows.

Run fetch explicitly with --env-file; no application configuration/database is
imported. Acquisition does not advance backend cursors or trigger analysis.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))


def fetch(env_file, out):
    import httpx
    from dotenv import dotenv_values
    configuration = dotenv_values(env_file)
    url = configuration["SENSOR_AGENT_URL"].rstrip("/")
    key = configuration["SENSOR_AGENT_API_KEY"]
    if not key or not url:
        raise ValueError("Explicit sensor URL and key are required")
    out.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=60, headers={"X-API-Key": key}) as client:
        response = client.get(url + "/files")
        response.raise_for_status()
        files = response.json()["files"]
        # This fresh boot's active log contains the current controlled run.
        selected = [file for file in files if not file["archived"]]
        if not selected:
            raise RuntimeError("Sensor exposes no active connection log")
        collected, reads = [], []
        for file in selected:
            offset = 0
            for _ in range(200):
                response = client.get(url + "/logs", params={"file": file["file"],
                    "file_id": file["file_id"], "offset": offset, "limit": 500})
                response.raise_for_status()
                batch = response.json()
                if batch["file_id"] != file["file_id"] or batch["offset"] != offset:
                    raise RuntimeError("Sensor identity/cursor changed during collection")
                collected.extend(batch["records"])
                reads.append({key: value for key, value in batch.items() if key != "records"})
                if not batch["has_more"]:
                    break
                if batch["next_offset"] <= offset:
                    raise RuntimeError("Non-advancing sensor read")
                offset = batch["next_offset"]
            else:
                raise RuntimeError("Explicit sensor collection budget exceeded")
    path = out / "sensor.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in collected))
    (out / "sensor-acquisition.json").write_text(json.dumps({"fetched": time.time(),
        "files": selected, "reads": reads, "rows": len(collected),
        "sha256": digest(path)}, indent=2))
    print(f"Collected {len(collected)} actual sensor records; no database/cursor writes")


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(2**20):
            result.update(chunk)
    return result.hexdigest()


def labelled_sensor(records, manifest):
    """Match a unique initiated five-tuple inside the bounded experiment window.

    Guest clocks may slew after headless startup. Attribution therefore uses the
    recorded socket tuple, not an assumed sub-second agreement between clocks.
    Ambiguous tuple reuse is excluded, and observed clock offsets are reported.
    A single attempted socket may produce multiple Zeek records (e.g. SYN retry).
    """
    import pandas as pd
    rows = pd.DataFrame(records)
    if rows.empty:
        raise ValueError("No captured sensor records")
    for name in ("duration", "orig_bytes", "resp_bytes", "orig_pkts", "resp_pkts", "service", "conn_state", "history"):
        if name not in rows:
            rows[name] = None
    attempts = pd.DataFrame(manifest).rename(columns={"source": "id.orig_h",
        "destination": "id.resp_h", "source_port": "id.orig_p", "destination_port": "id.resp_p"})
    keys = ["proto", "id.orig_h", "id.resp_h", "id.orig_p", "id.resp_p"]
    ambiguous = attempts.duplicated(keys, keep=False)
    invalid = attempts.phase.eq("udp_burst") & ~attempts.success
    unique = attempts.loc[~ambiguous & ~invalid]
    matched = rows.merge(unique, on=keys, how="inner", validate="many_to_one")
    matched = matched.loc[(matched.ts - matched.started).abs().lt(120)].copy()
    if matched.uid.duplicated().any():
        raise ValueError("Ambiguous scenario attribution to the same Zeek connection")
    matched["family"] = matched.phase
    observed = set(zip(matched["proto"], matched["id.orig_p"], matched["started"]))
    missing = [row for row in manifest if (row["proto"], row["source_port"], row["started"]) not in observed]
    return matched, {"sensor_rows": len(rows), "attempts": len(attempts), "matched": len(matched),
        "unmatched_attempts": len(missing), "unmatched_by_phase": pd.Series([row["phase"] for row in missing], dtype=str).value_counts().to_dict(),
        "matched_by_phase": matched.phase.value_counts().to_dict(),
        "unlabelled_background_rows": len(rows)-matched.uid.nunique(),
        "ambiguous_tuple_attempts_excluded": int(ambiguous.sum()),
        "incomplete_udp_scenarios_excluded": int(invalid.sum()),
        "guest_clock_difference_seconds": {"min": float((matched.ts-matched.started).min()) if len(matched) else None,
            "max": float((matched.ts-matched.started).max()) if len(matched) else None},
        "failed_benign_attempts": int(((~attempts.success) & attempts.label.eq(0)).sum()),
        "nonzero_missed_bytes": int(pd.to_numeric(matched.get("missed_bytes", pd.Series(0, index=matched.index))).gt(0).sum())}


def candidate_paths():
    selected = ROOT / "api/app/ai/models/selected.joblib"
    yield "deployed-cic2017", selected
    for source in ("cic", "ton"):
        for seed in (42, 43, 44):
            for kind in ("random_forest", "logistic_regression", "isolation_forest"):
                yield f"{source}-{kind}-{seed}", ROOT / f".ai-workspace/runs/{source}-endpoint_pairs-{seed}/{kind}.joblib"
    for path in sorted((ROOT / ".ai-workspace/extension/results_serial").glob("*.joblib")):
        if "endpoint_pairs-" in path.name:
            yield path.stem, path
    for path in sorted((ROOT / ".ai-workspace/live-study/models-v2").glob("*.joblib")):
        yield path.stem, path


def evaluate(input_path, manifest_path, out):
    import joblib
    import numpy as np
    import pandas as pd
    from threadpoolctl import threadpool_limits
    from ai.experiment import metrics
    from ai.study_prepare import enrich
    records = [json.loads(line) for line in input_path.read_text().splitlines() if line]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    rows, audit = labelled_sensor(records, manifest)
    if rows.empty:
        raise ValueError("No unambiguous scenario connections can be attributed")
    frame = enrich(rows)
    for field in ("label", "family", "round"):
        frame[field] = rows[field].to_numpy()
    outputs = {}
    expected_runtime_ids = set()
    expected = json.loads((ROOT / "api/app/ai/deployment.json").read_text())["sha256"]
    for name, path in candidate_paths():
        checksum = digest(path)
        if name == "deployed-cic2017" and checksum != expected:
            raise ValueError("Deployment baseline checksum changed")
        # These are only trusted local training outputs, never downloaded models.
        bundle = joblib.load(path)
        model = bundle["model"]
        if "model__n_jobs" in model.get_params():
            model.set_params(model__n_jobs=1)
        columns = bundle["feature_columns"]
        started = time.perf_counter()
        with threadpool_limits(limits=1):
            if bundle.get("kind") == "isolation_forest":
                scores = -model.score_samples(frame.loc[:, columns])
            else:
                scores = model.predict_proba(frame.loc[:, columns])[:, 1]
        if not np.isfinite(scores).all():
            raise ValueError("Nonfinite evaluation score")
        if name == "deployed-cic2017":
            expected_runtime_ids = set(np.flatnonzero(scores >= bundle["threshold"]) + 1)
        outputs[name] = {"sha256": checksum, "threshold": bundle["threshold"],
            "inference_ms": (time.perf_counter()-started)*1000,
            "overall": metrics(frame, scores, bundle["threshold"]),
            "rounds": {str(round_id): metrics(frame.loc[mask], scores[mask], bundle["threshold"])
                for round_id in sorted(frame["round"].unique()) if (mask := frame["round"].eq(round_id).to_numpy()).any()}}
        attempts = rows.loc[:, ["proto", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "started", "label", "family", "round"]].copy()
        attempts["score"] = scores
        attempts = attempts.groupby([column for column in attempts if column != "score"], as_index=False).score.max()
        outputs[name]["initiated_sockets"] = metrics(attempts, attempts.score.to_numpy(), bundle["threshold"])
        print(name, outputs[name]["overall"]["confusion_matrix"], flush=True)
        del model, bundle
    out.parent.mkdir(parents=True, exist_ok=True)
    from app.ai.detector import load_detector
    from app.ai.preparation import PreparedConnection
    from app.schemas.connection import ZeekLogItem
    actual = {record["uid"]: record for record in records}
    prepared = tuple(PreparedConnection(connection_id=index,
        record=ZeekLogItem.model_validate(actual[uid])) for index, uid in enumerate(rows.uid, 1))
    detector = load_detector()
    findings = [finding for offset in range(0, len(prepared), 500)
        for finding in detector.analyze_batch(prepared[offset:offset+500])]
    matrix = outputs["deployed-cic2017"]["overall"]["confusion_matrix"]
    actual_runtime_ids = {identity for finding in findings for identity in finding.connection_ids}
    if len(findings) != matrix[0][1] + matrix[1][1] or actual_runtime_ids != expected_runtime_ids:
        raise RuntimeError("Actual runtime AnalysisEngine disagrees with offline baseline")
    out.write_text(json.dumps({"sensor_sha256": digest(input_path),
        "manifest_sha256": digest(manifest_path), "audit": audit,
        "label_semantics": {"0": "Controlled benign requests, including legitimate connection failures",
            "1": "Controlled reconnaissance/load scenarios; load is not evidence of a confirmed DoS or distributed attack"},
        "runtime_engine_probe": {"name": detector.name, "version": detector.version,
            "validated_connections": len(prepared), "findings": len(findings),
            "agrees_with_offline_baseline": True, "database_accessed": False}, "models": outputs}, indent=2))
    rows.to_parquet(out.with_suffix(".parquet"), index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("fetch")
    collect.add_argument("--env-file", type=Path, required=True)
    collect.add_argument("--out", type=Path, required=True)
    score = commands.add_parser("evaluate")
    score.add_argument("--input", type=Path, required=True)
    score.add_argument("--manifest", type=Path, required=True)
    score.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "fetch":
        fetch(args.env_file, args.out)
    else:
        evaluate(args.input, args.manifest, args.out)


if __name__ == "__main__":
    main()
