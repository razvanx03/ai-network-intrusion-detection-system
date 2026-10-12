"""
Application Constants for AI University NIDS Backend.
Centralizes configuration defaults, route prefixes, security tokens,
severity levels, alert statuses, MITRE ATT&CK techniques, and attack classifications.
"""

# API Routing
API_PREFIX: str = "/api"
API_V1_PREFIX: str = API_PREFIX

# Router Prefixes
AUTH_ROUTE_PREFIX: str = "/auth"
CONNECTION_ROUTE_PREFIX: str = "/logs"
ALERT_ROUTE_PREFIX: str = "/alerts"
SYSTEM_ROUTE_PREFIX: str = "/system"

# Security & Authentication
TOKEN_TYPE_BEARER: str = "bearer"
COOKIE_ACCESS_TOKEN_KEY: str = "nids_access_token"

# Security Severity Levels
SEVERITY_CRITICAL: str = "CRITICAL"
SEVERITY_HIGH: str = "HIGH"
SEVERITY_MEDIUM: str = "MEDIUM"
SEVERITY_LOW: str = "LOW"

VALID_SEVERITIES = {
    SEVERITY_CRITICAL,
    SEVERITY_HIGH,
    SEVERITY_MEDIUM,
    SEVERITY_LOW,
}

# Alert Workflow Statuses
ALERT_STATUS_NEW: str = "NEW"
ALERT_STATUS_ACKNOWLEDGED: str = "ACKNOWLEDGED"
ALERT_STATUS_RESOLVED: str = "RESOLVED"
ALERT_STATUS_FALSE_POSITIVE: str = "FALSE_POSITIVE"

VALID_ALERT_STATUSES = {
    ALERT_STATUS_NEW,
    ALERT_STATUS_ACKNOWLEDGED,
    ALERT_STATUS_RESOLVED,
    ALERT_STATUS_FALSE_POSITIVE,
}

# MITRE ATT&CK Enterprise Techniques
MITRE_T1046: str = "T1046: Network Service Discovery"
MITRE_T1110: str = "T1110: Brute Force"
MITRE_T1498: str = "T1498: Denial of Service"
MITRE_T1071: str = "T1071: Application Layer Protocol Anomaly"

# Attack Types / Categories
ATTACK_PORT_SCAN: str = "Port Scan"
ATTACK_SSH_BRUTE_FORCE: str = "SSH Brute-Force"
ATTACK_DOS_SYN_FLOOD: str = "DoS / SYN Flood"
ATTACK_STATISTICAL_ANOMALY: str = "Statistical Anomaly"

# Sensor Agent Modes
SENSOR_MODE_MOCK: str = "mock_mode"
SENSOR_MODE_REMOTE: str = "remote_vm"
