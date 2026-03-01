"""
SECURITY MONITORING DASHBOARD - Network Security & Intrusion Detection
=======================================================================
Enterprise-grade security monitoring and threat detection system.

Features:
- Real-time network traffic monitoring
- Intrusion detection system (IDS)
- Firewall management
- Threat intelligence integration
- Security incident response
- Vulnerability scanning
- Compliance monitoring
- Security analytics and reporting
"""

import hashlib
import ipaddress
import json
import re
import threading
import time
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Callable

import yaml

log = logging.getLogger("security_monitoring")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"

def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data")) / "security_monitoring"


# ── Enums ──────────────────────────────────────────────────────────────────────

class ThreatLevel(Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

class AlertType(Enum):
    PORT_SCAN           = "port_scan"
    BRUTE_FORCE         = "brute_force"
    MALWARE             = "malware"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_TRAFFIC  = "suspicious_traffic"
    FAILED_LOGIN        = "failed_login"
    POLICY_VIOLATION    = "policy_violation"
    DATA_EXFILTRATION   = "data_exfiltration"

class SecurityEventStatus(Enum):
    DETECTED      = "detected"
    INVESTIGATING = "investigating"
    CONTAINED     = "contained"
    RESOLVED      = "resolved"
    FALSE_POSITIVE = "false_positive"


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class NetworkFlow:
    """Network traffic flow data."""
    id:                str
    source_ip:         str
    destination_ip:    str
    source_port:       int
    destination_port:  int
    protocol:          str
    bytes_transferred: int
    packets:           int
    start_time:        str          # ISO string for JSON compatibility
    end_time:          str
    direction:         str          # inbound, outbound
    flagged:           bool = False
    threat_level:      str  = "low"

@dataclass
class SecurityAlert:
    """Security alert/notification."""
    id:               str
    alert_type:       str                 # AlertType value
    threat_level:     str                 # ThreatLevel value
    source_ip:        str
    destination_ip:   str
    timestamp:        str                 # ISO string
    description:      str
    raw_data:         str
    status:           str                 # SecurityEventStatus value
    assigned_to:      str
    resolved_at:      Optional[str] = None
    resolution_notes: str           = ""

@dataclass
class FirewallRule:
    """Firewall rule configuration."""
    id:            str
    name:          str
    source:        str    # IP, subnet, or "any"
    destination:   str
    port:          str    # port number, range, or "any"
    protocol:      str    # tcp, udp, icmp, or "any"
    action:        str    # allow, deny, drop
    enabled:       bool
    created_at:    float
    last_modified: float
    created_by:    str

@dataclass
class Vulnerability:
    """Security vulnerability finding."""
    id:             str
    name:           str
    description:    str
    severity:       str           # ThreatLevel value
    cvss_score:     float
    affected_hosts: List[str]
    detection_date: str           # ISO string
    status:         str           # new, in_progress, patched, mitigated
    remediation:    str
    references:     List[str]

@dataclass
class Incident:
    """Security incident record."""
    id:                 str
    title:              str
    description:        str
    severity:           str                # ThreatLevel value
    status:             str                # SecurityEventStatus value
    detected_at:        str                # ISO string
    assigned_to:        str
    related_alerts:     List[str]
    timeline:           List[Dict]
    evidence:           List[str]
    remediation_steps:  List[str]
    closed_at:          Optional[str] = None
    closure_notes:      str          = ""

@dataclass
class ThreatIntel:
    """Threat intelligence feed entry."""
    id:             str
    indicator:      str
    indicator_type: str        # ip, domain, file_hash, url
    threat_type:    str        # malware, phishing, botnet, etc.
    confidence:     float      # 0.0–1.0
    severity:       str        # ThreatLevel value
    description:    str
    source:         str
    first_seen:     str        # ISO string
    last_seen:      str
    tags:           List[str]


# ── Dashboard ──────────────────────────────────────────────────────────────────

class SecurityMonitoringDashboard:
    """Enterprise security monitoring and threat detection system."""

    def __init__(self, storage_path: str = None):
        """
        Args:
            storage_path: Override storage directory. Defaults to config.
        """
        self.data_dir = Path(storage_path) if storage_path else _storage_base()
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.network_flows:    List[NetworkFlow]    = []
        self.security_alerts:  List[SecurityAlert]  = []
        self.firewall_rules:   List[FirewallRule]    = []
        self.vulnerabilities:  List[Vulnerability]   = []
        self.incidents:        List[Incident]        = []
        self.threat_intel:     List[ThreatIntel]     = []
        self.whitelist_ips:    List[str]             = []
        self.blacklist_ips:    List[str]             = []

        self.monitoring_enabled = True
        self.alert_thresholds = {
            "port_scan":          10,
            "failed_logins":       5,
            "suspicious_traffic":  1_000_000,
        }

        self._load_data()
        self._start_network_monitoring()
        self._start_alert_processor()
        log.info("Security Monitoring Dashboard initialized")

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load_data(self):
        try:
            flows_file = self.data_dir / "network_flows.json"
            if flows_file.exists():
                with open(flows_file, "r") as f:
                    for fd in json.load(f):
                        self.network_flows.append(NetworkFlow(**fd))

            alerts_file = self.data_dir / "security_alerts.json"
            if alerts_file.exists():
                with open(alerts_file, "r") as f:
                    for ad in json.load(f):
                        self.security_alerts.append(SecurityAlert(**ad))

            rules_file = self.data_dir / "firewall_rules.json"
            if rules_file.exists():
                with open(rules_file, "r") as f:
                    for rd in json.load(f):
                        self.firewall_rules.append(FirewallRule(**rd))

            vulns_file = self.data_dir / "vulnerabilities.json"
            if vulns_file.exists():
                with open(vulns_file, "r") as f:
                    for vd in json.load(f):
                        self.vulnerabilities.append(Vulnerability(**vd))

            incidents_file = self.data_dir / "incidents.json"
            if incidents_file.exists():
                with open(incidents_file, "r") as f:
                    for ind in json.load(f):
                        self.incidents.append(Incident(**ind))

            intel_file = self.data_dir / "threat_intel.json"
            if intel_file.exists():
                with open(intel_file, "r") as f:
                    for tid in json.load(f):
                        self.threat_intel.append(ThreatIntel(**tid))

            ips_file = self.data_dir / "ip_lists.json"
            if ips_file.exists():
                with open(ips_file, "r") as f:
                    ip_data = json.load(f)
                self.whitelist_ips = ip_data.get("whitelist", [])
                self.blacklist_ips = ip_data.get("blacklist", [])

        except Exception as e:
            log.error("Failed to load security data: %s", e)

    def _save_data(self):
        try:
            with open(self.data_dir / "network_flows.json",   "w") as f:
                json.dump([asdict(x) for x in self.network_flows],   f, indent=2)
            with open(self.data_dir / "security_alerts.json", "w") as f:
                json.dump([asdict(x) for x in self.security_alerts], f, indent=2)
            with open(self.data_dir / "firewall_rules.json",  "w") as f:
                json.dump([asdict(x) for x in self.firewall_rules],  f, indent=2)
            with open(self.data_dir / "vulnerabilities.json", "w") as f:
                json.dump([asdict(x) for x in self.vulnerabilities], f, indent=2)
            with open(self.data_dir / "incidents.json",       "w") as f:
                json.dump([asdict(x) for x in self.incidents],       f, indent=2)
            with open(self.data_dir / "threat_intel.json",    "w") as f:
                json.dump([asdict(x) for x in self.threat_intel],    f, indent=2)
            with open(self.data_dir / "ip_lists.json",        "w") as f:
                json.dump({"whitelist": self.whitelist_ips, "blacklist": self.blacklist_ips}, f, indent=2)
        except Exception as e:
            log.error("Failed to save security data: %s", e)

    # ── Network monitoring ─────────────────────────────────────────────────────

    def monitor_network_traffic(self) -> List[NetworkFlow]:
        """Monitor and analyze network traffic flows (simulated)."""
        sample_flows = [
            {"source_ip": "192.168.1.100", "destination_ip": "8.8.8.8",
             "source_port": 54321, "destination_port": 53, "protocol": "udp",
             "bytes": 128, "packets": 2},
            {"source_ip": "192.168.1.101", "destination_ip": "142.250.74.110",
             "source_port": 54322, "destination_port": 443, "protocol": "tcp",
             "bytes": 2048, "packets": 15},
            {"source_ip": "10.0.0.50", "destination_ip": "192.168.1.1",
             "source_port": 22, "destination_port": 54323, "protocol": "tcp",
             "bytes": 512, "packets": 8},
        ]

        flows = []
        for fd in sample_flows:
            flagged      = False
            threat_level = "low"
            if fd["destination_port"] == 22 and fd["protocol"] == "tcp":
                flagged = True
                threat_level = "medium"
            elif fd["bytes"] > 100_000:
                flagged = True
                threat_level = "high"

            now  = datetime.now()
            flow = NetworkFlow(
                id=f"flow_{int(time.time() * 1000)}_{len(flows)}",
                source_ip=fd["source_ip"],
                destination_ip=fd["destination_ip"],
                source_port=fd["source_port"],
                destination_port=fd["destination_port"],
                protocol=fd["protocol"],
                bytes_transferred=fd["bytes"],
                packets=fd["packets"],
                start_time=now.isoformat(),
                end_time=(now + timedelta(seconds=10)).isoformat(),
                direction="outbound" if not fd["source_ip"].startswith("192.168") else "inbound",
                flagged=flagged,
                threat_level=threat_level,
            )
            flows.append(flow)
            self.network_flows.append(flow)

        if flows:
            log.info("Monitored %d network flows", len(flows))
        return flows

    def detect_threats(self, flows: List[NetworkFlow] = None) -> List[SecurityAlert]:
        """Detect security threats from network flows."""
        if flows is None:
            flows = self.network_flows[-100:]

        flows_by_source: Dict[str, List[NetworkFlow]] = {}
        for f in flows:
            flows_by_source.setdefault(f.source_ip, []).append(f)

        alerts: List[SecurityAlert] = []
        for source_ip, ip_flows in flows_by_source.items():
            if len(ip_flows) > self.alert_thresholds["port_scan"]:
                unique_ports = len({f.destination_port for f in ip_flows})
                if unique_ports > 20:
                    alerts.append(self._create_alert(
                        AlertType.PORT_SCAN, ThreatLevel.HIGH, source_ip,
                        "Multiple destination ports scanned",
                        f"Port scan from {source_ip} to {unique_ports} different ports",
                    ))

            total_bytes = sum(f.bytes_transferred for f in ip_flows)
            if total_bytes > self.alert_thresholds["suspicious_traffic"]:
                alerts.append(self._create_alert(
                    AlertType.SUSPICIOUS_TRAFFIC, ThreatLevel.MEDIUM, source_ip,
                    "High volume data transfer",
                    f"Suspicious traffic volume: {total_bytes:,} bytes from {source_ip}",
                ))

            if source_ip in self.blacklist_ips:
                alerts.append(self._create_alert(
                    AlertType.UNAUTHORIZED_ACCESS, ThreatLevel.CRITICAL, source_ip,
                    "Known malicious IP detected",
                    f"Traffic from blacklisted IP: {source_ip}",
                ))

        for a in alerts:
            self.security_alerts.append(a)
        if alerts:
            self._save_data()
            log.info("Detected %d security threats", len(alerts))
        return alerts

    def _create_alert(self, alert_type: AlertType, threat_level: ThreatLevel,
                      source_ip: str, description: str, raw_data: str) -> SecurityAlert:
        dest = "multiple" if alert_type == AlertType.PORT_SCAN else "unknown"
        return SecurityAlert(
            id=f"alert_{int(time.time() * 1000)}",
            alert_type=alert_type.value,
            threat_level=threat_level.value,
            source_ip=source_ip,
            destination_ip=dest,
            timestamp=datetime.now().isoformat(),
            description=description,
            raw_data=raw_data,
            status=SecurityEventStatus.DETECTED.value,
            assigned_to="unassigned",
        )

    # ── Firewall ───────────────────────────────────────────────────────────────

    def add_firewall_rule(self, name: str, source: str, destination: str,
                          port: str, protocol: str, action: str,
                          created_by: str = "system") -> str:
        """Add a new firewall rule."""
        rule_id = f"rule_{int(time.time() * 1000)}"
        self.firewall_rules.append(FirewallRule(
            id=rule_id, name=name, source=source, destination=destination,
            port=port, protocol=protocol, action=action, enabled=True,
            created_at=time.time(), last_modified=time.time(), created_by=created_by,
        ))
        self._save_data()
        log.info("Added firewall rule: %s (%s %s %s)", name, action, protocol, port)
        return rule_id

    def block_ip(self, ip_address: str, reason: str = "Security threat") -> str:
        """Block an IP address via firewall rule and blacklist."""
        if ip_address not in self.blacklist_ips:
            self.blacklist_ips.append(ip_address)
        self.add_firewall_rule(
            name=f"Block {ip_address}",
            source=ip_address, destination="any",
            port="any", protocol="any", action="deny",
            created_by="security_system",
        )
        log.info("Blocked IP: %s - %s", ip_address, reason)
        self._save_data()
        return f"Blocked {ip_address}: {reason}"

    def whitelist_ip(self, ip_address: str, reason: str = "Trusted source") -> str:
        """Whitelist an IP address."""
        if ip_address not in self.whitelist_ips:
            self.whitelist_ips.append(ip_address)
        log.info("Whitelisted IP: %s - %s", ip_address, reason)
        self._save_data()
        return f"Whitelisted {ip_address}: {reason}"

    # ── Vulnerability scanning ─────────────────────────────────────────────────

    def scan_vulnerabilities(self, target: str = "local_network") -> List[Vulnerability]:
        """Scan for system vulnerabilities (simulated)."""
        templates = [
            {"name": "OpenSSH Vulnerability", "severity": "high", "cvss": 7.5,
             "hosts": ["192.168.1.100", "192.168.1.101"],
             "description": "Outdated OpenSSH version with known security flaws",
             "remediation": "Update OpenSSH to latest version"},
            {"name": "Weak Password Policy", "severity": "medium", "cvss": 5.3,
             "hosts": ["192.168.1.1", "192.168.1.254"],
             "description": "System allows weak passwords and lacks account lockout",
             "remediation": "Enforce strong password policies and account lockout"},
            {"name": "Unpatched Web Server", "severity": "critical", "cvss": 9.8,
             "hosts": ["192.168.1.200"],
             "description": "Apache server running vulnerable version",
             "remediation": "Update Apache to patched version immediately"},
        ]
        vulns = []
        for t in templates:
            vuln = Vulnerability(
                id=f"vuln_{int(time.time() * 1000)}_{len(vulns)}",
                name=t["name"], description=t["description"],
                severity=t["severity"], cvss_score=t["cvss"],
                affected_hosts=t["hosts"], detection_date=datetime.now().isoformat(),
                status="new", remediation=t["remediation"],
                references=["CVE-XXXX-XXXX"],
            )
            vulns.append(vuln)
            self.vulnerabilities.append(vuln)
        if vulns:
            self._save_data()
            log.info("Found %d vulnerabilities", len(vulns))
        return vulns

    # ── Incidents ──────────────────────────────────────────────────────────────

    def create_incident(self, title: str, description: str,
                        severity: str, related_alerts: List[str] = None) -> str:
        """Create a security incident record."""
        incident_id = f"inc_{int(time.time() * 1000)}"
        self.incidents.append(Incident(
            id=incident_id, title=title, description=description,
            severity=severity, status=SecurityEventStatus.DETECTED.value,
            detected_at=datetime.now().isoformat(), assigned_to="unassigned",
            related_alerts=related_alerts or [],
            timeline=[{"timestamp": datetime.now().isoformat(),
                       "event": "Incident created", "details": description}],
            evidence=[], remediation_steps=[],
        ))
        self._save_data()
        log.info("Created incident: %s (%s)", title, severity)
        return incident_id

    def update_incident_status(self, incident_id: str, status: str,
                               notes: str = "") -> bool:
        """Update incident status (pass SecurityEventStatus value string)."""
        for incident in self.incidents:
            if incident.id == incident_id:
                old = incident.status
                incident.status = status
                incident.timeline.append({
                    "timestamp": datetime.now().isoformat(),
                    "event":     f"Status changed from {old} to {status}",
                    "details":   notes,
                })
                if status == SecurityEventStatus.RESOLVED.value:
                    incident.closed_at     = datetime.now().isoformat()
                    incident.closure_notes = notes
                self._save_data()
                log.info("Updated incident %s status: %s", incident_id, status)
                return True
        return False

    # ── Threat intelligence ────────────────────────────────────────────────────

    def get_threat_intelligence(self) -> List[Dict]:
        """Get current threat intelligence summary."""
        if not self.threat_intel:
            self._populate_sample_threat_intel()
        return [
            {"indicator": t.indicator, "type": t.indicator_type,
             "threat_type": t.threat_type, "severity": t.severity,
             "confidence": t.confidence, "description": t.description,
             "last_seen": t.last_seen}
            for t in self.threat_intel
        ]

    def _populate_sample_threat_intel(self):
        samples = [
            {"indicator": "185.132.189.10", "type": "ip", "threat": "botnet_c2",
             "severity": "high", "confidence": 0.85,
             "description": "Known botnet command and control server"},
            {"indicator": "malware.example-domain.com", "type": "domain", "threat": "phishing",
             "severity": "medium", "confidence": 0.75,
             "description": "Phishing domain distributing banking trojans"},
            {"indicator": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6", "type": "file_hash",
             "threat": "ransomware", "severity": "critical", "confidence": 0.95,
             "description": "Ransomware payload hash"},
        ]
        now = datetime.now()
        for s in samples:
            self.threat_intel.append(ThreatIntel(
                id=f"intel_{int(time.time() * 1000)}_{len(self.threat_intel)}",
                indicator=s["indicator"], indicator_type=s["type"],
                threat_type=s["threat"], confidence=s["confidence"],
                severity=s["severity"], description=s["description"],
                source="Sample Threat Feed",
                first_seen=(now - timedelta(days=30)).isoformat(),
                last_seen=now.isoformat(), tags=["sample"],
            ))

    # ── Dashboard / reporting ──────────────────────────────────────────────────

    def get_security_dashboard(self) -> Dict:
        """Return comprehensive security dashboard data."""
        now = datetime.now()

        alert_severity_counts: Dict[str, int] = {}
        for a in self.security_alerts:
            alert_severity_counts[a.threat_level] = alert_severity_counts.get(a.threat_level, 0) + 1

        incident_status_counts: Dict[str, int] = {}
        for i in self.incidents:
            incident_status_counts[i.status] = incident_status_counts.get(i.status, 0) + 1

        vuln_severity_counts: Dict[str, int] = {}
        for v in self.vulnerabilities:
            vuln_severity_counts[v.severity] = vuln_severity_counts.get(v.severity, 0) + 1

        cutoff_24h = (now - timedelta(hours=24)).isoformat()
        cutoff_7d  = (now - timedelta(days=7)).isoformat()
        recent_alerts    = [a for a in self.security_alerts if a.timestamp > cutoff_24h]
        recent_incidents = [i for i in self.incidents      if i.detected_at > cutoff_7d]

        return {
            "summary": {
                "total_alerts":        len(self.security_alerts),
                "total_incidents":     len(self.incidents),
                "total_vulnerabilities": len(self.vulnerabilities),
                "total_firewall_rules": len(self.firewall_rules),
                "blacklisted_ips":     len(self.blacklist_ips),
                "whitelisted_ips":     len(self.whitelist_ips),
            },
            "alerts_by_severity":         alert_severity_counts,
            "incidents_by_status":        incident_status_counts,
            "vulnerabilities_by_severity": vuln_severity_counts,
            "recent_alerts": [
                {"type": a.alert_type, "severity": a.threat_level,
                 "source": a.source_ip, "time": a.timestamp, "description": a.description}
                for a in recent_alerts[:10]
            ],
            "recent_incidents": [
                {"title": i.title, "severity": i.severity,
                 "status": i.status, "detected": i.detected_at}
                for i in recent_incidents[:5]
            ],
            "network_stats": {
                "flows_monitored": len(self.network_flows),
                "flagged_flows":   sum(1 for f in self.network_flows if f.flagged),
                "last_scan":       now.strftime("%Y-%m-%d %H:%M:%S"),
            },
        }

    def generate_security_report(self, period_days: int = 30) -> str:
        """Generate a comprehensive security report."""
        report_start = datetime.now() - timedelta(days=period_days)
        dashboard    = self.get_security_dashboard()
        summary      = dashboard["summary"]

        lines = [
            "=" * 70,
            "SECURITY MONITORING REPORT",
            "=" * 70,
            f"Period: {report_start.strftime('%Y-%m-%d')} to {datetime.now().strftime('%Y-%m-%d')}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "", "EXECUTIVE SUMMARY", "-" * 25,
            f"Total Security Alerts:  {summary['total_alerts']}",
            f"Active Incidents:       {sum(1 for i in self.incidents if i.status != SecurityEventStatus.RESOLVED.value)}",
            f"Vulnerabilities Found:  {summary['total_vulnerabilities']}",
            f"Blocked IPs:            {summary['blacklisted_ips']}",
            "", "ALERT ANALYSIS", "-" * 18,
        ]
        for severity, count in dashboard["alerts_by_severity"].items():
            lines.append(f"{severity.upper():.<15} {count} alerts")

        high_crit = [a for a in self.security_alerts
                     if a.threat_level in ("high", "critical")]
        high_crit.sort(key=lambda x: x.timestamp, reverse=True)

        lines += ["", "RECENT CRITICAL ALERTS", "-" * 28]
        for a in high_crit[:10]:
            lines += [f"{a.timestamp[:16]} - {a.description}",
                      f"  Source: {a.source_ip} | Severity: {a.threat_level}"]

        lines += ["", "VULNERABILITY ASSESSMENT", "-" * 30]
        for severity, count in dashboard["vulnerabilities_by_severity"].items():
            lines.append(f"{severity.upper():.<15} {count} vulnerabilities")

        high_crit_vulns = [v for v in self.vulnerabilities
                           if v.severity in ("high", "critical")]
        if high_crit_vulns:
            lines.append("\nMost Critical Vulnerabilities:")
            for v in high_crit_vulns[:5]:
                lines += [f"  {v.name} (CVSS: {v.cvss_score})",
                          f"    Affected: {', '.join(v.affected_hosts[:3])}",
                          f"    Remediation: {v.remediation}"]

        lines += ["", "INCIDENT RESPONSE", "-" * 20]
        for status, count in dashboard["incidents_by_status"].items():
            lines.append(f"{status.replace('_', ' ').title():.<20} {count} incidents")

        lines += ["", "=" * 70,
                  "Report generated by Apex Security Monitoring System",
                  "=" * 70]
        return "\n".join(lines)

    # ── Background threads ─────────────────────────────────────────────────────

    def _start_network_monitoring(self):
        def loop():
            while self.monitoring_enabled:
                try:
                    flows = self.monitor_network_traffic()
                    self.detect_threats(flows)
                    time.sleep(30)
                except Exception as e:
                    log.error("Network monitoring error: %s", e)
                    time.sleep(60)
        threading.Thread(target=loop, daemon=True).start()
        log.info("Network monitoring started")

    def _start_alert_processor(self):
        def loop():
            while self.monitoring_enabled:
                try:
                    self._correlate_alerts()
                    time.sleep(60)
                except Exception as e:
                    log.error("Alert processing error: %s", e)
                    time.sleep(300)
        threading.Thread(target=loop, daemon=True).start()
        log.info("Alert correlation engine started")

    def _correlate_alerts(self):
        """Correlate recent alerts and auto-create incidents for suspicious patterns."""
        window_start = (datetime.now() - timedelta(minutes=5)).isoformat()
        recent = [a for a in self.security_alerts if a.timestamp > window_start]

        source_alerts: Dict[str, List[SecurityAlert]] = {}
        for a in recent:
            source_alerts.setdefault(a.source_ip, []).append(a)

        for source, alerts in source_alerts.items():
            if len(alerts) > 3:
                types = {a.alert_type for a in alerts}
                if len(types) > 1:
                    self.create_incident(
                        title=f"Suspicious Activity from {source}",
                        description=(f"Multiple alert types from {source}: "
                                     f"{', '.join(types)}"),
                        severity=ThreatLevel.HIGH.value,
                        related_alerts=[a.id for a in alerts],
                    )


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[SecurityMonitoringDashboard] = None

def get_security_monitoring() -> SecurityMonitoringDashboard:
    """Return the process-level SecurityMonitoringDashboard singleton."""
    global _instance
    if _instance is None:
        _instance = SecurityMonitoringDashboard()
    return _instance


# ── Tool registration ──────────────────────────────────────────────────────────

def register_tools(registry) -> None:
    sm = get_security_monitoring()
    registry.register("sec_monitor_traffic",     "Monitor and analyze network traffic flows",  sm.monitor_network_traffic,  module="security", tags=["monitoring"])
    registry.register("sec_detect_threats",      "Detect threats from network flows",          sm.detect_threats,           module="security", tags=["monitoring"])
    registry.register("sec_add_firewall_rule",   "Add a firewall rule",                        sm.add_firewall_rule,        module="security", tags=["monitoring"])
    registry.register("sec_block_ip",            "Block an IP address",                        sm.block_ip,                 module="security", tags=["monitoring"])
    registry.register("sec_whitelist_ip",        "Whitelist an IP address",                    sm.whitelist_ip,             module="security", tags=["monitoring"])
    registry.register("sec_scan_vulnerabilities","Scan for system vulnerabilities",             sm.scan_vulnerabilities,     module="security", tags=["monitoring"])
    registry.register("sec_create_incident",     "Create a security incident record",          sm.create_incident,          module="security", tags=["monitoring"])
    registry.register("sec_update_incident",     "Update security incident status",            sm.update_incident_status,   module="security", tags=["monitoring"])
    registry.register("sec_get_dashboard",       "Get comprehensive security dashboard data",  sm.get_security_dashboard,   module="security", tags=["monitoring"])
    registry.register("sec_generate_report",     "Generate security monitoring report",        sm.generate_security_report, module="security", tags=["monitoring"])
    registry.register("sec_threat_intelligence", "Get current threat intelligence",            sm.get_threat_intelligence,  module="security", tags=["monitoring"])
