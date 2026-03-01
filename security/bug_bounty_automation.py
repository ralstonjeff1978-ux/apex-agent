"""
BUG BOUNTY AUTOMATION - Ethical Hacking Toolkit
================================================
Automated security testing and vulnerability assessment.

Features:
- Automated web application scanning
- Network vulnerability detection
- Payload generation and testing
- Report generation
- Integration with popular security tools
"""

import json
import re
import subprocess
import time
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import yaml

log = logging.getLogger("bug_bounty")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"

def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data")) / "bug_bounty"


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class Vulnerability:
    """Represents a discovered security vulnerability."""
    id:            str
    type:          str    # sql_injection, xss, csrf, etc.
    severity:      str    # critical, high, medium, low, info
    url:           str
    parameter:     str
    description:   str
    evidence:      str
    remediation:   str
    discovered_at: float
    tool_used:     str

@dataclass
class ScanResult:
    """Results from a security scan."""
    target:          str
    scan_type:       str
    start_time:      float
    end_time:        float
    vulnerabilities: List[Vulnerability]
    informational:   List[str]
    errors:          List[str]
    summary:         Dict[str, int]   # count by severity


# ── Scanner ────────────────────────────────────────────────────────────────────

class BugBountyScanner:
    """Automated security scanner for authorized bug bounty engagements."""

    def __init__(self, storage_path: str = None):
        """
        Args:
            storage_path: Override results directory. Defaults to config.
        """
        self.results_dir = Path(storage_path) if storage_path else _storage_base()
        self.results_dir.mkdir(parents=True, exist_ok=True)

        try:
            import requests
            self._session = requests.Session()
            self._session.headers.update({"User-Agent": "Apex-BugBounty-Scanner/1.0"})
            self._requests_available = True
        except ImportError:
            self._session = None
            self._requests_available = False
            log.warning("requests library not available; HTTP scanning disabled")

        self.tools_available = self._check_required_tools()

    def _check_required_tools(self) -> Dict[str, bool]:
        """Check which external security tools are installed."""
        tools = {t: False for t in ("nmap", "sqlmap", "nikto", "gobuster", "whatweb")}
        for tool in tools:
            try:
                subprocess.run([tool, "--help"], capture_output=True, timeout=5)
                tools[tool] = True
                log.info("%s available", tool)
            except (subprocess.SubprocessError, FileNotFoundError):
                log.warning("%s not found — some features limited", tool)
        return tools

    # ── Public API ─────────────────────────────────────────────────────────────

    def scan_target(self, target: str, scan_types: List[str] = None) -> ScanResult:
        """Perform a comprehensive security scan on the target."""
        if not scan_types:
            scan_types = ["port_scan", "web_vuln", "directory_brute"]

        log.info("Starting security scan of %s", target)
        start_time = time.time()

        vulnerabilities: List[Vulnerability] = []
        informational:   List[str]           = []
        errors:          List[str]           = []
        summary = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}

        if "port_scan" in scan_types and self.tools_available["nmap"]:
            pv, pi, pe = self._nmap_scan(target)
            vulnerabilities.extend(pv); informational.extend(pi); errors.extend(pe)

        if "web_vuln" in scan_types:
            wv, wi, we = self._web_vulnerability_scan(target)
            vulnerabilities.extend(wv); informational.extend(wi); errors.extend(we)

        if "directory_brute" in scan_types and self.tools_available["gobuster"]:
            df, di, de = self._directory_brute_force(target)
            informational.extend(df); informational.extend(di); errors.extend(de)

        for vuln in vulnerabilities:
            summary[vuln.severity] = summary.get(vuln.severity, 0) + 1

        result = ScanResult(
            target=target, scan_type=", ".join(scan_types),
            start_time=start_time, end_time=time.time(),
            vulnerabilities=vulnerabilities, informational=informational,
            errors=errors, summary=summary,
        )
        self._save_scan_result(result)
        log.info("Scan completed: %s", summary)
        return result

    # ── Scan methods ───────────────────────────────────────────────────────────

    def _nmap_scan(self, target: str) -> Tuple[List[Vulnerability], List[str], List[str]]:
        vulns: List[Vulnerability] = []
        info:  List[str]           = []
        errs:  List[str]           = []
        try:
            safe_name = target.replace("http://", "").replace("https://", "").replace("/", "_")
            out_base  = str(self.results_dir / f"nmap_{safe_name}")
            result = subprocess.run(
                ["nmap", "-sV", "-sC", "--open", "-oA", out_base, target],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                output = result.stdout
                info.append(f"Nmap scan completed for {target}")
                vuln_services = ["vsftpd", "ProFTPD", "Apache Tomcat", "phpMyAdmin",
                                 "WordPress", "Joomla", "Drupal"]
                for service in vuln_services:
                    if service.lower() in output.lower():
                        vulns.append(Vulnerability(
                            id=f"nmap_{int(time.time())}",
                            type="service_vulnerability", severity="medium",
                            url=target, parameter=service,
                            description=f"Potentially vulnerable service detected: {service}",
                            evidence=output[:500],
                            remediation="Update service to latest version and review configuration",
                            discovered_at=time.time(), tool_used="nmap",
                        ))
            else:
                errs.append(f"Nmap failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            errs.append("Nmap scan timed out")
        except Exception as e:
            errs.append(f"Nmap error: {e}")
        return vulns, info, errs

    def _web_vulnerability_scan(self, target: str) -> Tuple[List[Vulnerability], List[str], List[str]]:
        vulns: List[Vulnerability] = []
        info:  List[str]           = []
        errs:  List[str]           = []
        try:
            for test_fn in (self._test_sql_injection, self._test_xss,
                            self._test_headers):
                try:
                    v, i, e = test_fn(target)
                    vulns.extend(v); info.extend(i); errs.extend(e)
                except Exception as ex:
                    errs.append(f"Test {test_fn.__name__} failed: {ex}")
        except Exception as e:
            errs.append(f"Web vulnerability scan error: {e}")
        return vulns, info, errs

    def _test_sql_injection(self, target: str) -> Tuple[List[Vulnerability], List[str], List[str]]:
        vulns: List[Vulnerability] = []
        info  = ["SQL injection testing completed"]
        errs: List[str]           = []
        if not self._requests_available:
            return vulns, info, errs
        try:
            payloads = ["' OR '1'='1", "' UNION SELECT NULL--", "'; DROP TABLE users--"]
            parsed   = urlparse(target)
            if parsed.scheme and parsed.netloc:
                for payload in payloads:
                    try:
                        resp = self._session.get(target, params={"id": payload, "search": payload}, timeout=10)
                        sql_errors = ["mysql_fetch", "sql syntax", "ORA-", "PostgreSQL",
                                      "ODBC", "JDBC", "SQLite", "SQLServer"]
                        for err in sql_errors:
                            if err.lower() in resp.text.lower():
                                vulns.append(Vulnerability(
                                    id=f"sqli_{int(time.time())}",
                                    type="sql_injection", severity="high",
                                    url=target, parameter="id/search",
                                    description="Potential SQL injection vulnerability detected",
                                    evidence=f"SQL error signature found: {err}",
                                    remediation="Use parameterized queries and input validation",
                                    discovered_at=time.time(), tool_used="manual_test",
                                ))
                                break
                    except Exception as e:
                        errs.append(f"SQLi test request failed: {e}")
        except Exception as e:
            errs.append(f"SQL injection test error: {e}")
        return vulns, info, errs

    def _test_xss(self, target: str) -> Tuple[List[Vulnerability], List[str], List[str]]:
        vulns: List[Vulnerability] = []
        info  = ["XSS testing completed"]
        errs: List[str]           = []
        if not self._requests_available:
            return vulns, info, errs
        try:
            payloads = ["<script>alert(1)</script>", '"><script>alert(document.cookie)</script>',
                        "javascript:alert(1)", "<img src=x onerror=alert(1)>"]
            parsed   = urlparse(target)
            if parsed.scheme and parsed.netloc:
                for payload in payloads:
                    try:
                        resp = self._session.get(
                            target, params={"q": payload, "search": payload}, timeout=10
                        )
                        if payload in resp.text and "alert(1)" in resp.text:
                            vulns.append(Vulnerability(
                                id=f"xss_{int(time.time())}",
                                type="cross_site_scripting", severity="high",
                                url=target, parameter="q/search",
                                description="Potential XSS vulnerability detected",
                                evidence=f"XSS payload reflected: {payload[:50]}",
                                remediation="Implement proper output encoding and input validation",
                                discovered_at=time.time(), tool_used="manual_test",
                            ))
                    except Exception as e:
                        errs.append(f"XSS test request failed: {e}")
        except Exception as e:
            errs.append(f"XSS test error: {e}")
        return vulns, info, errs

    def _test_headers(self, target: str) -> Tuple[List[Vulnerability], List[str], List[str]]:
        vulns: List[Vulnerability] = []
        info:  List[str]           = []
        errs:  List[str]           = []
        if not self._requests_available:
            info.append("HTTP headers test skipped (requests unavailable)")
            return vulns, info, errs
        try:
            resp    = self._session.get(target, timeout=10)
            headers = resp.headers
            security_headers = {
                "X-Frame-Options":        "Missing protection against clickjacking",
                "X-Content-Type-Options": "Missing MIME type sniffing protection",
                "X-XSS-Protection":       "Missing XSS protection header",
                "Strict-Transport-Security": "Missing HSTS header",
                "Content-Security-Policy": "Missing CSP header",
            }
            for header, description in security_headers.items():
                if header not in headers:
                    vulns.append(Vulnerability(
                        id=f"headers_{int(time.time())}",
                        type="missing_security_header", severity="medium",
                        url=target, parameter=header,
                        description=f"Missing security header: {header}",
                        evidence=f"Header {header} not present in response",
                        remediation=description,
                        discovered_at=time.time(), tool_used="manual_test",
                    ))
            for h in ("X-Powered-By", "Server"):
                if h in headers:
                    info.append(f"Information disclosure: {h} = {headers[h]}")
            info.append("HTTP headers analysis completed")
        except Exception as e:
            errs.append(f"Headers test failed: {e}")
        return vulns, info, errs

    def _directory_brute_force(self, target: str) -> Tuple[List[str], List[str], List[str]]:
        findings: List[str] = []
        info:     List[str] = []
        errs:     List[str] = []
        if not self.tools_available["gobuster"]:
            info.append("Gobuster not available for directory brute force")
            return findings, info, errs
        try:
            common_dirs = ["admin", "login", "wp-admin", "administrator", "config",
                           "backup", "db", "database", "sql", "mysql", "phpmyadmin",
                           "test", "dev", "development", "debug", "logs", "log"]
            wordlist = self.results_dir / "common_dirs.txt"
            wordlist.write_text("\n".join(common_dirs))
            result = subprocess.run(
                ["gobuster", "dir", "-u", target, "-w", str(wordlist),
                 "-t", "10", "-o", str(self.results_dir / "gobuster_output.txt")],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode in (0, 1):
                findings.append("Directory brute force completed")
                if result.stdout:
                    findings.extend(result.stdout.split("\n"))
            else:
                errs.append(f"Gobuster failed: {result.stderr}")
        except subprocess.TimeoutExpired:
            errs.append("Gobuster timed out")
        except Exception as e:
            errs.append(f"Directory brute force error: {e}")
        return findings, info, errs

    # ── Persistence ────────────────────────────────────────────────────────────

    def _save_scan_result(self, result: ScanResult):
        try:
            data = {
                "target": result.target, "scan_type": result.scan_type,
                "start_time": result.start_time, "end_time": result.end_time,
                "vulnerabilities": [asdict(v) for v in result.vulnerabilities],
                "informational": result.informational,
                "errors": result.errors, "summary": result.summary,
            }
            filename = self.results_dir / f"scan_{int(result.start_time)}.json"
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            log.info("Scan results saved to %s", filename.name)
        except Exception as e:
            log.error("Failed to save scan results: %s", e)

    # ── Reporting ──────────────────────────────────────────────────────────────

    def generate_report(self, scan_result: ScanResult) -> str:
        """Generate a human-readable security report."""
        lines = [
            "=" * 60, "APEX SECURITY SCAN REPORT", "=" * 60,
            f"Target:    {scan_result.target}",
            f"Scan Type: {scan_result.scan_type}",
            f"Duration:  {scan_result.end_time - scan_result.start_time:.2f} seconds",
            "", "VULNERABILITY SUMMARY", "-" * 30,
        ]
        for severity, count in scan_result.summary.items():
            if count > 0:
                lines.append(f"{severity.upper()}: {count}")

        high_crit = [v for v in scan_result.vulnerabilities if v.severity in ("critical", "high")]
        if high_crit:
            lines += ["", "HIGH RISK VULNERABILITIES", "-" * 40]
            for v in high_crit:
                lines += [f"[{v.severity.upper()}] {v.type}",
                          f"  URL:         {v.url}",
                          f"  Parameter:   {v.parameter}",
                          f"  Description: {v.description}",
                          f"  Remediation: {v.remediation}", ""]

        medium = [v for v in scan_result.vulnerabilities if v.severity == "medium"]
        if medium:
            lines += ["MEDIUM RISK VULNERABILITIES", "-" * 40]
            for v in medium:
                lines += [f"[{v.severity.upper()}] {v.type}",
                          f"  URL:         {v.url}",
                          f"  Description: {v.description}", ""]

        if scan_result.informational:
            lines += ["INFORMATIONAL FINDINGS", "-" * 30]
            for info in scan_result.informational[:10]:
                lines.append(f"  {info}")
            if len(scan_result.informational) > 10:
                lines.append(f"  ... and {len(scan_result.informational) - 10} more")

        if scan_result.errors:
            lines += ["", "ERRORS DURING SCAN", "-" * 25]
            for err in scan_result.errors:
                lines.append(f"  {err}")

        lines += ["", "=" * 60,
                  "Generated by Apex Bug Bounty Automation",
                  "=" * 60]
        return "\n".join(lines)


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[BugBountyScanner] = None

def get_bug_bounty_scanner() -> BugBountyScanner:
    """Return the process-level BugBountyScanner singleton."""
    global _instance
    if _instance is None:
        _instance = BugBountyScanner()
    return _instance


# ── Tool registration ──────────────────────────────────────────────────────────

def register_tools(registry) -> None:
    scanner = get_bug_bounty_scanner()
    registry.register("bugbounty_scan_target",    "Run a comprehensive security scan on a target", scanner.scan_target,    module="security", tags=["bugbounty"])
    registry.register("bugbounty_generate_report","Generate a human-readable scan report",         scanner.generate_report, module="security", tags=["bugbounty"])
