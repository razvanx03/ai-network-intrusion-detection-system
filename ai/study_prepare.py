"""Normalize extension sources; preserve split metadata, never use labels as features."""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from ai.study_acquire import ROOT, STUDY, CTU_FILES, digest
sys.path.insert(0, str(ROOT / "api"))
from app.ai.features import COUNTERS, FEATURE_COLUMNS, feature_frame
from ai.prepare import pair_groups

DERIVED = ("log1p_orig_payload_per_packet", "log1p_resp_payload_per_packet",
           "log1p_packet_rate", "log1p_payload_rate", "orig_payload_fraction",
           "orig_packet_fraction", "zero_duration", "missing_rate")
HISTORY = tuple(f"history_{flag}" for flag in "SHADFRshadfr") + ("history_missing",)


def enrich(raw):
    """Independent-connection features available from existing stored log fields."""
    output = feature_frame(raw)
    values = {name: pd.to_numeric(raw[name].replace("-", np.nan), errors="raise") for name in COUNTERS}
    duration = values["duration"]
    packets = values["orig_pkts"] + values["resp_pkts"]
    payload = values["orig_bytes"] + values["resp_bytes"]
    for direction in ("orig", "resp"):
        ratio = values[f"{direction}_bytes"] / values[f"{direction}_pkts"].where(values[f"{direction}_pkts"].gt(0))
        output[f"log1p_{direction}_payload_per_packet"] = np.log1p(ratio.fillna(0))
    output["log1p_packet_rate"] = np.log1p((packets / duration.where(duration.gt(0))).fillna(0))
    output["log1p_payload_rate"] = np.log1p((payload / duration.where(duration.gt(0))).fillna(0))
    output["orig_payload_fraction"] = (values["orig_bytes"] / payload.where(payload.gt(0))).fillna(0)
    output["orig_packet_fraction"] = (values["orig_pkts"] / packets.where(packets.gt(0))).fillna(0)
    output["zero_duration"] = duration.eq(0).astype(float)
    output["missing_rate"] = (duration.isna() | packets.isna() | payload.isna()).astype(float)
    history = raw["history"].fillna("-").astype(str)
    for flag in "SHADFRshadfr":
        output[f"history_{flag}"] = history.str.contains(flag, regex=False).astype(float)
    output["history_missing"] = history.isin(["-", ""]).astype(float)
    if not np.isfinite(output.loc[:, list(DERIVED) + list(HISTORY)].to_numpy(dtype=float)).all():
        raise ValueError("Nonfinite derived feature")
    return output


def read_zeek(path):
    fields = None
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if line.startswith("#fields"):
                fields = line.rstrip("\n").split("\t")[1:]
                break
    if fields is None:
        raise ValueError(f"Missing Zeek schema: {path}")
    # Some labelers append three space-delimited label columns under one header.
    table = pd.read_csv(path, sep="\t", comment="#", names=fields,
                        dtype=str, keep_default_na=False, low_memory=False)
    return table


def prepare(dataset):
    audit = {"dataset": dataset, "files": []}
    manifests = []
    if dataset == "ctu":
        manifests = [STUDY / (name + ".sources.json") for name in CTU_FILES]
    elif dataset == "uwf":
        manifests = [STUDY / "uwf.sources.json"]
    verified = {}
    for manifest in manifests:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        entries = data["logs"] if dataset == "ctu" else data
        verified.update({item["path"]: item["sha256"] for item in entries})
    if dataset == "cic":
        paths = sorted((ROOT / ".ai-workspace/raw/cic").glob("*.parquet"))
    else:
        paths = sorted((STUDY / f"raw/{dataset}").rglob("*.parquet" if dataset == "uwf" else "*.tsv"))
    if not paths:
        raise FileNotFoundError(f"No {dataset} sources available")
    tables = []
    for path in paths:
        if manifests and digest(path) != verified[path.relative_to(ROOT).as_posix()]:
            raise ValueError(f"Acquisition fingerprint changed: {path}")
        raw = read_zeek(path) if dataset == "ctu" else pd.read_parquet(path)
        before = len(raw)
        raw = raw.drop_duplicates().reset_index(drop=True)
        exact_removed = before - len(raw)
        raw = raw.rename(columns={"src_ip_zeek": "id.orig_h", "dest_ip_zeek": "id.resp_h",
                                  "src_port_zeek": "id.orig_p", "dest_port_zeek": "id.resp_p"})
        unknown = 0
        if dataset == "uwf":
            flags = raw.label_binary.astype(str).str.lower()
            unknown = int((~flags.isin(["true", "false", "duplicate"])).sum())
            if unknown:
                raise ValueError(f"Unknown UWF binary label encoding: {raw.label_binary.unique()}")
            # Duplicate denotes secondary annotations, not an independent flow.
            raw = raw.loc[flags.isin(["true", "false"])].copy()
            raw["target"] = raw.label_binary.str.lower().eq("true").astype(int)
            raw["family"] = raw.label_tactic.astype(str).str.lower().where(raw.target.eq(1), "benign")
        elif dataset == "ctu":
            label_columns = [column for column in raw if "label" in column.lower()]
            if "label" not in raw:
                if len(label_columns) != 1:
                    raise ValueError(f"Unrecognized CTU labels: {list(raw.columns)}")
                pieces = raw[label_columns[0]].str.split(expand=True)
                if pieces.shape[1] != 3:
                    raise ValueError(f"Unrecognized compound CTU label: {pieces.head()}")
                raw["label"], raw["detailed_label"] = pieces[1], pieces[2]
            label = raw.label.str.lower()
            known = label.isin(["benign", "malicious"])
            unknown = int((~known).sum())
            raw = raw.loc[known].copy()
            raw["target"] = raw.label.str.lower().eq("malicious").astype(int)
            detail = next((column for column in raw if "detailed" in column.lower()), "label")
            raw["family"] = raw[detail].str.lower().where(raw.target.eq(1), "benign")
        else:
            raw["target"] = ~raw.label.str.lower().eq("benign")
            raw["family"] = raw.label.str.lower()
        for name in COUNTERS:
            raw[name] = pd.to_numeric(raw[name].replace({"-": np.nan, "": np.nan}), errors="raise")
        raw["ts"] = pd.to_numeric(raw.ts, errors="raise")
        if not np.isfinite(raw.ts).all():
            raise ValueError("Invalid timestamps")
        # A UID may be repeated across label rows/files. Contradictions are
        # rejected later; identifiers remain grouping metadata, not predictors.
        raw["identity"] = raw.uid.astype(str) + "|" + raw.ts.astype(str)
        prepared = enrich(raw)
        prepared["group"] = pair_groups(raw["id.orig_h"], raw["id.resp_h"])
        prepared["family"] = raw.family
        prepared["label"] = raw.target.astype(int)
        prepared["event_time"] = raw.ts
        prepared["duration_raw"] = raw.duration.fillna(0)
        prepared["capture"] = path.parent.name if dataset != "cic" else path.stem
        prepared["day"] = pd.to_datetime(raw.ts, unit="s", utc=True).dt.strftime("%Y-%m-%d")
        prepared["identity"] = pd.util.hash_pandas_object(raw.identity, index=False).astype(str)
        tables.append(prepared.reset_index(drop=True))
        audit["files"].append(dict(path=path.relative_to(ROOT).as_posix(), sha256=digest(path),
            raw_rows=before, exact_duplicates_removed=exact_removed, excluded_unknown_labels=unknown,
            retained_rows=len(prepared), label_counts=prepared.label.value_counts().to_dict()))
        print(dataset, path.name, before, "->", len(prepared), flush=True)
    result = pd.concat(tables, ignore_index=True)
    consistency = result.groupby("identity").label.nunique()
    conflicting = set(consistency[consistency.gt(1)].index)
    audit["contradictory_identities_excluded"] = len(conflicting)
    result = result.loc[~result.identity.isin(conflicting)]
    prior = len(result)
    result = result.drop_duplicates("identity").reset_index(drop=True)
    audit["duplicate_identities_removed"] = prior - len(result)
    audit.update(rows=len(result), groups=int(result.group.nunique()),
                 labels=result.label.value_counts().to_dict(), families=result.family.value_counts().to_dict(),
                 days=result.groupby(["day", "label"]).size().reset_index(name="rows").to_dict("records"))
    target = STUDY / "prepared"
    target.mkdir(parents=True, exist_ok=True)
    result.to_parquet(target / f"{dataset}.parquet", index=False)
    (target / f"{dataset}.audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in audit.items() if key != "files"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+", choices=["cic", "uwf", "ctu"], required=True)
    for name in parser.parse_args().datasets:
        prepare(name)
