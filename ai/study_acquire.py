"""Acquire official, bounded extension-study sources without touching deployment.

python -m ai.study_acquire --source uwf
python -m ai.study_acquire --source ctu
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import html
import json
from pathlib import Path
import re
import tarfile
import time
from urllib.parse import urljoin

import httpx

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT / ".ai-workspace" / "extension"
UWF = "https://datasets.uwf.edu/data/UWF-ZeekData24/parquet/"
CTU = "https://zenodo.org/records/7958259/files/"
# Two Windows endpoints plus one non-workstation transfer challenge. The Ubuntu
# flood-dominated archive is deliberately not used as a representative sample.
CTU_FILES = {
    "CTU-SME-11_Experiment-VM-Microsoft-Windows7AD-1_v1.0.0.tar.bz2": "c97f72da16c46c5176bac52ad2101f0f",
    "CTU-SME-11_Experiment-VM-Microsoft-Windows7full-1_v1.0.0.tar.bz2": "e4c0d3abe56c15257bf019824f202284",
    "CTU-SME-11_Honeypot-Assistant-Amazon-Echo1stGen-1_v1.0.0.tar.bz2": "311cbd100eeddf76c8056919fe35b0cb",
}


def digest(path, algorithm="sha256"):
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def links(client, url):
    response = client.get(url)
    response.raise_for_status()
    return [html.unescape(value) for value in re.findall(r'href="([^"]+)"', response.text)]


def download(url, target, expected_md5=None, expected_sha256=None):
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        partial = target.with_suffix(target.suffix + ".partial")
        started = last = time.monotonic()
        size = 0
        with httpx.Client(timeout=120, follow_redirects=True) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                if "text/html" in response.headers.get("content-type", ""):
                    raise ValueError("Source returned HTML instead of data")
                with partial.open("wb") as output:
                    for block in response.iter_bytes(1024 * 1024):
                        output.write(block)
                        size += len(block)
                        if time.monotonic() - last > 15:
                            print(f"Download {target.name}: {size / 1e6:.1f} MB, {time.monotonic()-started:.0f}s", flush=True)
                            last = time.monotonic()
        if expected_md5 and digest(partial, "md5") != expected_md5:
            raise ValueError(f"Publisher checksum mismatch: {target.name}")
        if expected_sha256 and digest(partial) != expected_sha256:
            raise ValueError(f"Previously acquired source changed: {target.name}")
        partial.replace(target)
    if expected_md5 and digest(target, "md5") != expected_md5:
        raise ValueError(f"Cached source failed publisher checksum: {target.name}")
    if expected_sha256 and digest(target) != expected_sha256:
        raise ValueError(f"Cached source fingerprint changed: {target.name}")
    result = dict(url=url, path=target.relative_to(ROOT).as_posix(), bytes=target.stat().st_size,
                  sha256=digest(target), publisher_md5=expected_md5)
    print(json.dumps(result), flush=True)
    return result


def acquire_uwf():
    sources = []
    manifest = STUDY / "uwf.sources.json"
    previous = {item["path"]: item["sha256"] for item in json.loads(manifest.read_text())} if manifest.exists() else {}
    with httpx.Client(timeout=60) as client:
        weeks = sorted(value for value in links(client, UWF) if value.startswith("2024-") and value.endswith("/"))
        if not weeks:
            raise ValueError("No dated UWF partitions available")
        for week in weeks:
            url = urljoin(UWF, week)
            for file in links(client, url):
                if file.endswith(".parquet") and Path(file).name == file:
                    target = STUDY / "raw/uwf" / week[:10] / file
                    sources.append(download(urljoin(url, file), target,
                                            expected_sha256=previous.get(target.relative_to(ROOT).as_posix())))
    (STUDY / "uwf.sources.json").write_text(json.dumps(sources, indent=2), encoding="utf-8")


def acquire_ctu_file(item):
    filename, checksum = item
    target = STUDY / "raw/ctu/archives" / filename
    result = download(CTU + filename + "?download=1", target, checksum)
    outputs = []
    # Never extract PCAPs, executables, symbolic links or archive-controlled paths.
    with tarfile.open(target, "r|bz2") as archive:
        for member in archive:
            if member.isfile() and member.name.endswith("/conn.log.labeled"):
                identity = hashlib.sha256(member.name.encode()).hexdigest()[:20]
                destination = STUDY / "raw/ctu/logs" / filename.removesuffix(".tar.bz2") / f"{identity}.tsv"
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not destination.exists():
                    with archive.extractfile(member) as source, destination.open("wb") as output:
                        for block in iter(lambda: source.read(1024 * 1024), b""):
                            output.write(block)
                outputs.append(dict(member=member.name, path=destination.relative_to(ROOT).as_posix(),
                                    sha256=digest(destination), bytes=destination.stat().st_size))
                print(f"Extracted connection logs: {member.name}", flush=True)
    if not outputs:
        raise ValueError(f"No labelled connection logs found in {filename}")
    result["logs"] = outputs
    manifest = STUDY / (filename + ".sources.json")
    manifest.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["uwf", "ctu"], required=True)
    args = parser.parse_args()
    if args.source == "uwf":
        acquire_uwf()
    else:
        with ThreadPoolExecutor(max_workers=2) as executor:
            list(executor.map(acquire_ctu_file, CTU_FILES.items()))


if __name__ == "__main__":
    main()
