import datetime
from typing import List, Dict, Any, Tuple
import numpy as np
from sklearn.ensemble import IsolationForest
from app.core.constants import (
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    ALERT_STATUS_NEW,
    MITRE_T1046,
    MITRE_T1110,
    MITRE_T1498,
    MITRE_T1071,
    ATTACK_PORT_SCAN,
    ATTACK_SSH_BRUTE_FORCE,
    ATTACK_DOS_SYN_FLOOD,
    ATTACK_STATISTICAL_ANOMALY,
)


class IntrusionDetectionEngine:
    """
    Hybrid Intrusion Detection Engine combining:
    1. L4/L7 Session Metadata Behavioral Heuristics (Port Scan, Brute-Force, DoS)
    2. Unsupervised Statistical Anomaly Detection (Isolation Forest)
    """

    def __init__(self):
        # Isolation Forest baseline for anomaly detection on network flow features
        self.anomaly_detector = IsolationForest(
            n_estimators=100,
            contamination=0.08,
            random_state=42
        )
        self.is_fitted = False
        self._init_baseline_model()

    def _init_baseline_model(self):
        """Fit Isolation Forest on typical normal baseline network flow features."""
        # Simulated normal network traffic distributions:
        # [duration (s), orig_bytes, resp_bytes, orig_pkts, resp_pkts]
        rng = np.random.default_rng(42)
        normal_durations = rng.uniform(0.1, 10.0, size=(200, 1))
        normal_orig_bytes = rng.normal(800, 300, size=(200, 1)).clip(40, 10000)
        normal_resp_bytes = rng.normal(3500, 1200, size=(200, 1)).clip(40, 50000)
        normal_orig_pkts = rng.integers(5, 30, size=(200, 1))
        normal_resp_pkts = rng.integers(5, 40, size=(200, 1))

        X_baseline = np.hstack([
            normal_durations,
            normal_orig_bytes,
            normal_resp_bytes,
            normal_orig_pkts,
            normal_resp_pkts
        ])
        self.anomaly_detector.fit(X_baseline)
        self.is_fitted = True

    def analyze_batch(self, connections: List[dict]) -> List[dict]:
        """
        Analyze a batch of Zeek connection dictionaries and return generated alerts.
        """
        alerts: List[dict] = []
        if not connections:
            return alerts

        # Aggregation structures for behavioral heuristics
        src_port_scan_tracker: Dict[str, set] = {}
        src_ssh_tracker: Dict[str, int] = {}
        dst_dos_tracker: Dict[str, int] = {}

        for conn in connections:
            src_ip = conn.get("src_ip", "")
            dst_ip = conn.get("dst_ip", "")
            dst_port = conn.get("dst_port", 0)
            conn_state = conn.get("conn_state", "")

            # Track unique destination ports for scan detection
            if conn_state in ["S0", "REJ", "RSTOS0"]:
                if src_ip not in src_port_scan_tracker:
                    src_port_scan_tracker[src_ip] = set()
                src_port_scan_tracker[src_ip].add(dst_port)

            # Track SSH connection volume
            if dst_port == 22 or conn.get("service") == "ssh":
                src_ssh_tracker[src_ip] = src_ssh_tracker.get(src_ip, 0) + 1

            # Track DoS connection bursts
            dst_dos_tracker[dst_ip] = dst_dos_tracker.get(dst_ip, 0) + 1

        # 1. Port Scanning Detection (MITRE T1046)
        for src_ip, ports in src_port_scan_tracker.items():
            if len(ports) >= 5:  # threshold for port scanning behavior
                alerts.append({
                    "timestamp": datetime.datetime.now(datetime.timezone.utc),
                    "connection_id": None,
                    "src_ip": src_ip,
                    "dst_ip": "Multiple Targets",
                    "dst_port": None,
                    "attack_type": ATTACK_PORT_SCAN,
                    "severity": SEVERITY_HIGH,
                    "confidence": min(0.70 + (len(ports) * 0.02), 0.99),
                    "detector": "HeuristicEngine (State S0/REJ Cluster)",
                    "description": f"Host {src_ip} scanned {len(ports)} distinct ports without completing handshakes (conn_state S0/REJ).",
                    "mitre_technique": MITRE_T1046,
                    "status": ALERT_STATUS_NEW
                })

        # 2. SSH Brute Force Detection (MITRE T1110)
        for src_ip, count in src_ssh_tracker.items():
            if count >= 4:
                alerts.append({
                    "timestamp": datetime.datetime.now(datetime.timezone.utc),
                    "connection_id": None,
                    "src_ip": src_ip,
                    "dst_ip": "SSH Server (Port 22)",
                    "dst_port": 22,
                    "attack_type": ATTACK_SSH_BRUTE_FORCE,
                    "severity": SEVERITY_CRITICAL,
                    "confidence": min(0.75 + (count * 0.03), 0.98),
                    "detector": "HeuristicEngine (SSH Session Spike)",
                    "description": f"High volume of repeated SSH connection attempts ({count} flows) detected from {src_ip}.",
                    "mitre_technique": MITRE_T1110,
                    "status": ALERT_STATUS_NEW
                })

        # 3. DoS / SYN Flood Detection (MITRE T1498)
        for dst_ip, count in dst_dos_tracker.items():
            if count >= 30:
                alerts.append({
                    "timestamp": datetime.datetime.now(datetime.timezone.utc),
                    "connection_id": None,
                    "src_ip": "Distributed / Flooder",
                    "dst_ip": dst_ip,
                    "dst_port": None,
                    "attack_type": ATTACK_DOS_SYN_FLOOD,
                    "severity": SEVERITY_CRITICAL,
                    "confidence": 0.95,
                    "detector": "HeuristicEngine (Traffic Rate Spike)",
                    "description": f"Target host {dst_ip} received sudden burst of {count} flows in single window.",
                    "mitre_technique": MITRE_T1498,
                    "status": ALERT_STATUS_NEW
                })

        # 4. Statistical Anomaly Detection (Isolation Forest)
        features_list = []
        valid_indices = []
        for idx, c in enumerate(connections):
            dur = float(c.get("duration") or 0.0)
            orig_b = float(c.get("orig_bytes") or 0)
            resp_b = float(c.get("resp_bytes") or 0)
            orig_p = float(c.get("orig_pkts") or 0)
            resp_p = float(c.get("resp_pkts") or 0)
            features_list.append([dur, orig_b, resp_b, orig_p, resp_p])
            valid_indices.append(idx)

        if features_list and self.is_fitted:
            X = np.array(features_list)
            scores = self.anomaly_detector.decision_function(X)
            preds = self.anomaly_detector.predict(X)

            for i, (pred, score) in enumerate(zip(preds, scores)):
                # pred == -1 means anomaly
                if pred == -1 and score < -0.12:
                    conn = connections[valid_indices[i]]
                    # Avoid duplicate alert if already captured by port scan
                    if conn.get("dst_port") != 22 and conn.get("conn_state") != "S0":
                        alerts.append({
                            "timestamp": datetime.datetime.now(datetime.timezone.utc),
                            "connection_id": None,
                            "src_ip": conn.get("src_ip", ""),
                            "dst_ip": conn.get("dst_ip", ""),
                            "dst_port": conn.get("dst_port"),
                            "attack_type": ATTACK_STATISTICAL_ANOMALY,
                            "severity": SEVERITY_MEDIUM,
                            "confidence": round(float(abs(score)), 2),
                            "detector": "IsolationForest Anomaly Detector",
                            "description": f"Abnormal flow metrics detected: {conn.get('orig_bytes')} bytes / {conn.get('duration')}s duration (anomaly score: {score:.3f}).",
                            "mitre_technique": MITRE_T1071,
                            "status": ALERT_STATUS_NEW
                        })

        return alerts


# Singleton instance
detector_engine = IntrusionDetectionEngine()
