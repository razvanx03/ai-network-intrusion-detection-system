"""Acquire only selected network captures; downloaded data never becomes code."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile
import zlib

import httpx

from ai.remote_zip import RemoteZip
from ai.live_study import digest

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".ai-workspace/live-study"
CAPTURES = {"wed": ("Wednesday-14-02-2018", "pcap/UCAP172.31.69.25"),
            "thu": ("Thursday-15-02-2018", "pcap/UCAP172.31.69.25"),
            "fri": ("Friday-16-02-2018", "pcap/UCAP172.31.69.25-part1.pcap")}
for day, (folder, _) in list(CAPTURES.items()):
    for suffix, address in (("a", "172.31.64.89"), ("b", "172.31.65.99")):
        CAPTURES[f"{day}-client-{suffix}"] = (folder, f"pcap/capWIN-J6GMIG1DQE5-{address}")


def acquire_2018():
    directory = WORK / "cic2018"
    directory.mkdir(parents=True, exist_ok=True)
    manifest = []
    for day, (folder, member) in CAPTURES.items():
        url = "https://cse-cic-ids2018.s3.ca-central-1.amazonaws.com/Original%20Network%20Traffic%20and%20Log%20data/" + folder + "/pcap.zip"
        target = directory / (f"{day}-victim.pcap" if len(day) == 3 else f"{day}.pcap")
        with RemoteZip(url) as remote, zipfile.ZipFile(remote) as archive:
            info = archive.getinfo(member)
            if info.file_size > 5_000_000_000:
                raise ValueError("Capture exceeds the reviewed size budget")
            if target.exists():
                crc = 0
                with target.open("rb") as stream:
                    while chunk := stream.read(8 * 2**20):
                        crc = zlib.crc32(chunk, crc)
                if target.stat().st_size != info.file_size or crc != info.CRC:
                    raise ValueError("Existing capture disagrees with publisher ZIP CRC/size")
            else:
                temporary = target.with_suffix(".partial")
                with archive.open(info) as source, temporary.open("wb") as output:
                    while chunk := source.read(8 * 2**20):
                        output.write(chunk)
                temporary.replace(target)
            manifest.append({"url": url, "member": member, "size": info.file_size,
                "zip_crc32": info.CRC, "etag": remote.etag, "sha256": digest(target),
                "downloaded_archive_bytes": remote.transferred, "path": target.relative_to(ROOT).as_posix()})
            print(day, info.file_size, "verified", flush=True)
    (directory / "sources.json").write_text(json.dumps(manifest, indent=2))


def acquire_2019():
    directory = WORK / "cic2019"
    directory.mkdir(parents=True, exist_ok=True)
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        response = client.get("https://zenodo.org/api/records/17121740")
        response.raise_for_status()
        record = response.json()
        (directory / "record.json").write_text(json.dumps(record, indent=2))
        sources = []
        for file in record["files"]:
            if not file["key"].endswith(".pcap"):
                continue
            if file["size"] > 12_000_000:
                raise ValueError("Derivative capture size changed beyond the reviewed budget")
            target = directory / file["key"]
            if not target.exists():
                response = client.get(file["links"]["self"])
                response.raise_for_status()
                target.write_bytes(response.content)
            content = target.read_bytes()
            if len(content) != file["size"] or "md5:" + hashlib.md5(content).hexdigest() != file["checksum"]:
                raise ValueError("2019 derivative capture failed publisher checksum")
            sources.append({"file": file["key"], "url": file["links"]["self"],
                "publisher_checksum": file["checksum"], "sha256": digest(target), "size": len(content)})
            print(file["key"], "verified", flush=True)
        (directory / "sources.json").write_text(json.dumps(sources, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", choices=["cic2018", "cic2019"])
    args = parser.parse_args()
    (acquire_2018 if args.dataset == "cic2018" else acquire_2019)()
