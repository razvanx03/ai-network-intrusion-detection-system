"""Synthetic evidence only: no VM, dataset, configuration or deployed artifact IO."""
import struct
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ai.cic_followup import label_2018
from ai.live_study import labelled_sensor
from ai.pcap_extract import audit_pcap


def attempt(raw_record, **changes):
    row = dict(source=raw_record["id.orig_h"], destination=raw_record["id.resp_h"],
        source_port=raw_record["id.orig_p"], destination_port=raw_record["id.resp_p"],
        proto="tcp", started=raw_record["ts"]-15, ended=raw_record["ts"]-14,
        phase="benign_https", label=0, round=1, success=True)
    return {**row, **changes}


def test_guest_clock_skew_does_not_hide_known_tuple_or_label_background(raw_record):
    background = {**raw_record, "uid": "background", "id.orig_p": 51001}
    matched, audit = labelled_sensor([raw_record, background], [attempt(raw_record)])
    assert matched.uid.tolist() == [raw_record["uid"]]
    assert audit["unlabelled_background_rows"] == 1
    assert audit["guest_clock_difference_seconds"]["min"] == 15


def test_reused_tuple_is_not_arbitrarily_assigned_to_a_scenario(raw_record):
    matched, audit = labelled_sensor([raw_record], [attempt(raw_record),
        attempt(raw_record, phase="http_load", label=1, round=2)])
    assert matched.empty
    assert audit["ambiguous_tuple_attempts_excluded"] == 2


def test_socket_retry_can_make_several_zeek_records_without_extra_attempts(raw_record):
    retry = {**raw_record, "uid": "retry", "ts": raw_record["ts"]+1}
    matched, audit = labelled_sensor([raw_record, retry], [attempt(raw_record)])
    assert len(matched) == 2
    assert audit["attempts"] == 1
    assert audit["unmatched_attempts"] == 0


def test_cic_closed_port_and_empty_ssh_attempts_are_not_confirmed_bruteforce():
    common = {"id.resp_h": "172.31.69.25", "duration": 1., "history": "Sr", "resp_bytes": 0}
    rows = pd.DataFrame([
        {**common, "id.orig_h": "18.221.219.4", "id.resp_p": 21, "ts": 1518618807., "orig_bytes": 0},
        {**common, "id.orig_h": "13.58.98.64", "id.resp_p": 22, "ts": 1518631320., "orig_bytes": 0},
        {**common, "id.orig_h": "13.58.98.64", "id.resp_p": 22, "ts": 1518631320., "orig_bytes": 80},
        {**common, "id.orig_h": "13.58.98.64", "id.resp_p": 22, "ts": 1518630000., "orig_bytes": 80},
    ])
    assert label_2018(rows, "wed").tolist() == ["ftp_attempted", "attempted_no_payload", "ssh_bruteforce", "unresolved"]


def test_pcap_audit_preserves_source_and_identifies_incomplete_terminal_record(tmp_path):
    header = struct.pack("<IHHIIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)
    complete = struct.pack("<IIII", 123, 500000, 4, 4) + b"abcd"
    truncated = struct.pack("<IIII", 124, 0, 9, 9) + b"abc"
    path = tmp_path / "synthetic.pcap"
    path.write_bytes(header+complete+truncated)
    audit = audit_pcap(path)
    assert audit["packets"] == 1
    assert audit["first_ts"] == 123.5
    assert audit["complete_prefix_bytes"] == len(header+complete)
    assert path.read_bytes() == header+complete+truncated


def test_pcapng_audit_checks_block_boundaries_and_timestamps(tmp_path):
    def block(kind, payload):
        size = len(payload)+12
        return struct.pack("<II", kind, size)+payload+struct.pack("<I", size)
    section = block(0x0a0d0d0a, struct.pack("<IHHq", 0x1a2b3c4d, 1, 0, -1))
    interface = block(1, struct.pack("<HHI", 1, 0, 65535))
    packet = block(6, struct.pack("<IIIII", 0, 0, 1000000, 4, 4)+b"abcd")
    path = tmp_path / "synthetic.pcapng"
    path.write_bytes(section+interface+packet+b"tail")
    audit = audit_pcap(path)
    assert audit["packets"] == 1
    assert audit["first_ts"] == 1
    assert audit["incomplete_tail_bytes"] == 4
    path.write_bytes(section+interface+packet[:-4]+b"xxxx")
    with pytest.raises(ValueError, match="trailing block length"):
        audit_pcap(path)
