"""Inspect public ZIP members with bounded HTTP range requests, not a full download.

No archive paths are extracted. A selected member is written to an explicit path
with a caller-specified uncompressed size budget and ZIP CRC verification.
"""
import argparse
import io
import json
from pathlib import Path
import zipfile

import httpx


class RemoteZip(io.RawIOBase):
    def __init__(self, url, block_size=8 * 2**20):
        self.client = httpx.Client(timeout=120, follow_redirects=True)
        self.url = url
        response = self.client.head(url)
        response.raise_for_status()
        self.size = int(response.headers["content-length"])
        self.etag = response.headers.get("etag")
        self.position = 0
        self.block_size = block_size
        self.cache = b""
        self.cache_start = -1
        self.transferred = 0

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.position

    def seek(self, offset, whence=0):
        self.position = offset + (0 if whence == 0 else self.position if whence == 1 else self.size)
        if self.position < 0:
            raise ValueError("Negative seek")
        return self.position

    def read(self, length=-1):
        length = self.size - self.position if length < 0 else min(length, self.size - self.position)
        chunks = []
        while length > 0:
            offset = self.position - self.cache_start
            if not 0 <= offset < len(self.cache):
                start = self.position
                end = min(start + max(length, self.block_size), self.size) - 1
                headers = {"Range": f"bytes={start}-{end}"}
                if self.etag:
                    headers["If-Match"] = self.etag
                response = self.client.get(self.url, headers=headers)
                if response.status_code != 206 or response.headers.get("content-range") != f"bytes {start}-{end}/{self.size}":
                    raise RuntimeError("Server did not honor the exact range / source changed")
                self.cache = response.content
                self.cache_start = start
                self.transferred += len(self.cache)
                offset = 0
            count = min(length, len(self.cache) - offset)
            chunks.append(self.cache[offset:offset+count])
            self.position += count
            length -= count
        return b"".join(chunks)

    def close(self):
        self.client.close()
        super().close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("--member")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-bytes", type=int, default=2_000_000_000)
    args = parser.parse_args()
    with RemoteZip(args.url) as remote, zipfile.ZipFile(remote) as archive:
        entries = [{"name": item.filename, "bytes": item.file_size,
                    "compressed": item.compress_size, "crc32": item.CRC,
                    "header_offset": item.header_offset} for item in archive.infolist()]
        if not args.member:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps({"url": args.url, "size": remote.size,
                "etag": remote.etag, "members": entries, "transferred": remote.transferred}, indent=2))
            print(json.dumps({"members": len(entries), "transferred": remote.transferred}))
        else:
            item = archive.getinfo(args.member)
            if item.file_size > args.max_bytes:
                raise ValueError("Selected member exceeds the explicit size budget")
            args.out.parent.mkdir(parents=True, exist_ok=True)
            temporary = args.out.with_suffix(args.out.suffix + ".partial")
            with archive.open(item) as source, temporary.open("wb") as target:
                while chunk := source.read(2**20):
                    target.write(chunk)
            temporary.replace(args.out)
            print(json.dumps({"member": item.filename, "bytes": item.file_size,
                              "transferred": remote.transferred}))


if __name__ == "__main__":
    main()
