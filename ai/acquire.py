"""Download only the network subset and published Zeek-derived connection data.

Run from the repository root: python -m ai.acquire
No downloaded source code or serialized model is executed.
"""
import hashlib
import json
from pathlib import Path
import time

import httpx

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".ai-workspace"
TON_REVISION = "b953d9388d2db3bc392ea7150476e4f219a2a1cb"
TON_URL = (f"https://huggingface.co/datasets/codymlewis/TON_IoT_network/resolve/"
           f"{TON_REVISION}/train_test_network.csv")
TON_SHA256 = "26ddc513552de36de6428b2e578efaed2b57504c716dfba847cc0109a64e1974"
ZENODO_RECORD = "21469685"


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def download(client: httpx.Client, url: str, path: Path, checksum: str) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    algorithm, expected = checksum.split(":", 1)
    if not path.exists():
        temporary = path.with_suffix(path.suffix + ".partial")
        with client.stream("GET", url) as response:
            response.raise_for_status()
            if "text/html" in response.headers.get("content-type", ""):
                raise RuntimeError(f"Expected data, received an HTML page: {url}")
            with temporary.open("wb") as stream:
                for block in response.iter_bytes(1024 * 1024):
                    stream.write(block)
        if digest(temporary, algorithm) != expected:
            raise ValueError(f"Checksum mismatch: {temporary}")
        temporary.replace(path)
    if digest(path, algorithm) != expected:
        raise ValueError(f"Existing file failed verification: {path}")
    result = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
              "url": url, "bytes": path.stat().st_size,
              "publisher_checksum": checksum, "sha256": digest(path)}
    print(json.dumps(result), flush=True)
    return result


def main() -> None:
    WORK.mkdir(exist_ok=True)
    with httpx.Client(follow_redirects=True, timeout=120) as client:
        records = [download(client, TON_URL, WORK / "raw/ton/train_test_network.csv",
                            f"sha256:{TON_SHA256}")]
        response = client.get(f"https://zenodo.org/api/records/{ZENODO_RECORD}")
        response.raise_for_status()
        metadata = response.json()
        (WORK / "raw/cic").mkdir(parents=True, exist_ok=True)
        (WORK / "raw/cic/record.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        for item in metadata["files"]:
            if item["key"].endswith((".parquet", ".csv")):
                if Path(item["key"]).name != item["key"]:
                    raise ValueError("Source metadata contains an invalid filename")
                records.append(download(client, item["links"]["self"],
                                        WORK / "raw/cic" / item["key"], item["checksum"]))
    manifest = {"created_unix": time.time(), "files": records,
                "ton_official_url": "https://research.unsw.edu.au/projects/toniot-datasets",
                "ton_mirror_revision": TON_REVISION,
                "cic_official_url": "https://www.unb.ca/cic/datasets/ids-2017.html",
                "cic_derivative_doi": "https://doi.org/10.5281/zenodo.21469685",
                "ton_source": "Community mirror; official source currently redirects to sign-in.",
                "cic_source": "Published Zeek re-extraction of original CIC-IDS2017 PCAPs; not CICFlowMeter CSVs."}
    (WORK / "sources.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
