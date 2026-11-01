"""Offline Zeek extraction inside the Linux VM; never changes live services.

Audits classic PCAP record boundaries, preserves the source, and removes only
an incomplete terminal record in a separate copy if necessary. Never replays
downloaded attack traffic onto a network.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import time


def audit_pcap(path):
    size = path.stat().st_size
    with path.open("rb") as stream:
        header = stream.read(24)
        if header[:4] == b"\x0a\x0d\x0d\x0a":
            return audit_pcapng(path)
        formats = {b"\xd4\xc3\xb2\xa1": ("<", 1e6), b"\xa1\xb2\xc3\xd4": (">", 1e6),
                   b"\x4d\x3c\xb2\xa1": ("<", 1e9), b"\xa1\xb2\x3c\x4d": (">", 1e9)}
        if len(header) != 24 or header[:4] not in formats:
            raise ValueError("Expected a complete classic PCAP header")
        endian, resolution = formats[header[:4]]
        good, count, first, last = 24, 0, None, None
        while stream.tell() < size:
            record = stream.read(16)
            if len(record) != 16:
                break
            sec, fraction, captured, original = struct.unpack(endian + "IIII", record)
            if captured > 16 * 2**20 or captured > original:
                raise ValueError("Invalid PCAP packet size")
            if stream.tell() + captured > size:
                break
            stream.seek(captured, 1)
            good = stream.tell()
            timestamp = sec + fraction / resolution
            first = timestamp if first is None else min(first, timestamp)
            last = timestamp if last is None else max(last, timestamp)
            count += 1
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 2**20):
            digest.update(chunk)
    return {"bytes": size, "complete_prefix_bytes": good, "incomplete_tail_bytes": size-good,
            "packets": count, "first_ts": first, "last_ts": last,
            "link_type": struct.unpack(endian + "I", header[20:24])[0], "sha256": digest.hexdigest()}


def audit_pcapng(path):
    size = path.stat().st_size
    good, count, first, last, interfaces = 0, 0, None, None, []
    endian = None
    with path.open("rb") as stream:
        while stream.tell() < size:
            position = stream.tell()
            head = stream.read(12)
            if len(head) < 12:
                break
            if head[:4] == b"\x0a\x0d\x0d\x0a":
                endian = {b"\x4d\x3c\x2b\x1a": "<", b"\x1a\x2b\x3c\x4d": ">"}.get(head[8:12])
                interfaces = []
            if endian is None:
                raise ValueError("PCAPNG section has no valid byte order")
            kind, length = struct.unpack(endian + "II", head[:8])
            if length < 12 or length % 4 or length > 16 * 2**20:
                raise ValueError("Invalid PCAPNG block length")
            if position + length > size:
                break
            stream.seek(position)
            block = stream.read(length)
            if struct.unpack(endian + "I", block[-4:])[0] != length:
                raise ValueError("Inconsistent PCAPNG trailing block length")
            if kind == 1:
                resolution, offset = 1e6, 0
                index = 16
                while index + 4 <= length - 4:
                    code, width = struct.unpack(endian + "HH", block[index:index+4])
                    if code == 0:
                        break
                    if code == 9 and width == 1:
                        value = block[index+4]
                        resolution = 2**(value & 127) if value & 128 else 10**value
                    elif code == 14 and width == 8:
                        offset = struct.unpack(endian + "q", block[index+4:index+12])[0]
                    index += 4 + ((width + 3) // 4) * 4
                interfaces.append((resolution, offset))
            elif kind == 6:
                interface, high, low = struct.unpack(endian + "III", block[8:20])
                if interface >= len(interfaces):
                    raise ValueError("PCAPNG packet references an unknown interface")
                resolution, offset = interfaces[interface]
                timestamp = ((high << 32) + low) / resolution + offset
                first = timestamp if first is None else min(first, timestamp)
                last = timestamp if last is None else max(last, timestamp)
                count += 1
            elif kind in (2, 3):
                raise ValueError("Unsupported legacy PCAPNG packet block")
            good = stream.tell()
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(8 * 2**20):
            digest.update(chunk)
    return {"format": "pcapng", "bytes": size, "complete_prefix_bytes": good,
        "incomplete_tail_bytes": size-good, "packets": count, "first_ts": first,
        "last_ts": last, "sha256": digest.hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--zeek", type=Path, default=Path("/opt/zeek/bin/zeek"))
    parser.add_argument("--verify-checksums", action="store_true")
    parser.add_argument("--filter", help="Explicit symmetric packet filter retaining both flow directions")
    args = parser.parse_args()
    source = args.source.resolve(strict=True)
    args.out.mkdir(parents=True, exist_ok=False)
    directory = args.out.resolve()
    audit = audit_pcap(source)
    extraction_source = source
    if audit["incomplete_tail_bytes"]:
        extraction_source = directory / "complete-prefix.pcap"
        with source.open("rb") as original, extraction_source.open("wb") as target:
            remaining = audit["complete_prefix_bytes"]
            while remaining:
                chunk = original.read(min(8 * 2**20, remaining))
                target.write(chunk)
                remaining -= len(chunk)
    command = [str(args.zeek)] + ([] if args.verify_checksums else ["-C"])
    if args.filter:
        # Validate filtering in an explicit libpcap stage. In the inspected
        # Zeek 9 build, -f was logged as installed for the PCAPNG input while
        # unselected TCP tuples still reached conn.log. Do not trust that flag
        # as evidence that the same cohort was used for every capture format.
        filtered = directory / "cohort.pcap"
        prefilter = ["tcpdump", "-nn", "-r", str(extraction_source), "-s", "0", "-w", str(filtered), args.filter]
        with (directory / "prefilter.stderr").open("w") as stderr:
            result = subprocess.run(prefilter, stdout=subprocess.DEVNULL, stderr=stderr, timeout=900)
        if result.returncode:
            raise RuntimeError("Offline libpcap filtering failed")
        audit["prefilter_command"] = prefilter
        audit["prefilter_audit"] = audit_pcap(filtered)
        extraction_source = filtered
    command += ["-r", str(extraction_source), "policy/tuning/json-logs"]
    started = time.monotonic()
    with (directory / "stdout").open("w") as stdout, (directory / "stderr").open("w") as stderr:
        result = subprocess.run(command, cwd=directory, stdout=stdout, stderr=stderr, timeout=900)
    audit.update(command=command, returncode=result.returncode, seconds=time.monotonic()-started,
        version=subprocess.check_output([str(args.zeek), "--version"], text=True).strip())
    (directory / "extraction.json").write_text(json.dumps(audit, indent=2))
    if result.returncode:
        raise RuntimeError(f"Zeek extraction failed; inspect {directory / 'stderr'}")
    print(json.dumps(audit), flush=True)


if __name__ == "__main__":
    main()
