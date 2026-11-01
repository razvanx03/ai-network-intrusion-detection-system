"""Temporary, bounded traffic target and capture for an explicitly owned VM lab.

Run inside the Ubuntu gateway as root, never on the host. Existing Zeek and
sensor services are not stopped or reconfigured. All outputs are local to --out.
"""
import argparse
import http.server
import ipaddress
import json
from pathlib import Path
import signal
import socket
import subprocess
import threading
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", required=True)
    parser.add_argument("--client", required=True)
    parser.add_argument("--interface", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seconds", type=int, default=420)
    args = parser.parse_args()
    if not all(ipaddress.ip_address(ip).is_private for ip in (args.bind, args.client)):
        parser.error("Only private, explicitly owned lab addresses are permitted")
    if not 30 <= args.seconds <= 900:
        parser.error("Capture duration must be between 30 and 900 seconds")
    args.out.mkdir(parents=True, exist_ok=False)

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            try:
                size = int(self.path.strip("/"))
            except ValueError:
                self.send_error(400)
                return
            if size not in (1024, 16384, 262144):
                self.send_error(400)
                return
            payload = b"NIDS lab payload\n" * (size // 17 + 1)
            self.send_response(200)
            self.send_header("Content-Length", str(size))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(payload[:size])

        def log_message(self, *_):
            pass

    httpd = http.server.ThreadingHTTPServer((args.bind, 18080), Handler)
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.bind((args.bind, 18081))
    udp.settimeout(.2)
    done = threading.Event()

    def echo():
        while not done.is_set():
            try:
                data, address = udp.recvfrom(2048)
                if address[0] == args.client:
                    udp.sendto(data, address)
            except socket.timeout:
                continue

    capture_log = (args.out / "tcpdump.stderr").open("w")
    capture = subprocess.Popen(["tcpdump", "-i", args.interface, "-B", "32768", "-s", "0", "-U",
        "-w", str(args.out / "traffic.pcap"), "host", args.client], stderr=capture_log)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    threading.Thread(target=echo, daemon=True).start()
    (args.out / "ready.json").write_text(json.dumps({"started": time.time(),
        "bind": args.bind, "client": args.client, "interface": args.interface}))
    try:
        for _ in range(args.seconds):
            if (args.out / "finish").exists():
                break
            if capture.poll() is not None:
                raise RuntimeError("tcpdump exited before capture completed")
            time.sleep(1)
    finally:
        done.set()
        httpd.shutdown()
        udp.close()
        if capture.poll() is None:
            capture.send_signal(signal.SIGINT)
            capture.wait(timeout=10)
        capture_log.close()
        (args.out / "finished.json").write_text(json.dumps({"finished": time.time(),
            "tcpdump_returncode": capture.returncode}))


if __name__ == "__main__":
    main()
