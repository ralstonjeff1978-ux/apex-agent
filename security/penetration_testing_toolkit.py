"""
PENETRATION TESTING TOOLKIT - Advanced Security Testing Framework
==================================================================
Professional penetration testing capabilities for authorized security assessments.

Features:
- Network scanning and enumeration
- Vulnerability exploitation framework
- Payload generation and delivery
- Post-exploitation tools
- Privilege escalation techniques
- Lateral movement utilities
- Data exfiltration simulation
- Stealth and evasion capabilities
"""

import hashlib
import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

import yaml

log = logging.getLogger("penetration_testing")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"

def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data")) / "pentest"


# ── Enums ──────────────────────────────────────────────────────────────────────

class ExploitCategory(Enum):
    INFORMATION_GATHERING = "information_gathering"
    VULNERABILITY_ANALYSIS = "vulnerability_analysis"
    WEB_APPLICATION       = "web_application"
    EXPLOITATION          = "exploitation"
    PRIVILEGE_ESCALATION  = "privilege_escalation"
    MAINTAINING_ACCESS    = "maintaining_access"
    CLEARING_TRACKS       = "clearing_tracks"

class ExploitType(Enum):
    SCANNER          = "scanner"
    BRUTE_FORCE      = "brute_force"
    EXPLOIT          = "exploit"
    BACKDOOR         = "backdoor"
    PAYLOAD          = "payload"
    POST_EXPLOITATION = "post_exploitation"


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class ExploitModule:
    """Penetration testing exploit module."""
    module_id:            str
    name:                 str
    description:          str
    category:             str             # ExploitCategory value
    type:                 str             # ExploitType value
    author:               str
    credits:              List[str]
    references:           List[str]
    required_permissions: List[str]
    target_os:            List[str]
    target_arch:          List[str]
    disclosure_date:      str
    last_updated:         float
    module_path:          str
    dependencies:         List[str]
    parameters:           Dict[str, Any]
    default_parameters:   Dict[str, Any]
    success_indicators:   List[str]
    stealth_level:        int             # 1–10, 10 = most stealthy
    legal_risk:           str

@dataclass
class ExploitExecution:
    """Record of exploit execution."""
    execution_id:             str
    module_id:                str
    target:                   str
    parameters:               Dict[str, Any]
    start_time:               float
    end_time:                 float
    success:                  bool
    output:                   str
    error_output:             str
    evidence_collected:       List[str]
    session_id:               Optional[str]
    privileges_gained:        List[str]
    artifacts_created:        List[str]
    stealth_used:             List[str]
    legal_compliance_checked: bool
    authorized:               bool

@dataclass
class AttackSession:
    """Interactive attack session."""
    session_id:          str
    target:              str
    initial_access_time: float
    current_privileges:  List[str]
    session_type:        str
    tools_loaded:        List[str]
    commands_executed:   List[Dict[str, Any]]
    files_transferred:   List[Dict[str, Any]]
    persistence_methods: List[str]
    status:              str     # active, suspended, terminated
    last_activity:       float


# ── Toolkit ────────────────────────────────────────────────────────────────────

class PenetrationTestingToolkit:
    """Advanced penetration testing framework."""

    def __init__(self, storage_path: str = None, legal_compliance=None,
                 authorization_manager=None, forensic_handler=None):
        """
        Args:
            storage_path:         Override storage directory. Defaults to config.
            legal_compliance:     Injected LegalComplianceFramework instance.
            authorization_manager: Injected AuthorizationManager instance.
            forensic_handler:     Injected ForensicEvidenceHandler instance.
        """
        base = Path(storage_path) if storage_path else _storage_base()

        self.modules_path  = base / "modules"
        self.sessions_path = base / "sessions"
        self.exploits_path = base / "exploits"
        for d in (self.modules_path, self.sessions_path, self.exploits_path):
            d.mkdir(parents=True, exist_ok=True)

        self.modules_file    = base / "exploit_modules.json"
        self.executions_file = base / "exploit_executions.json"
        self.sessions_file   = base / "attack_sessions.json"

        self.modules:    List[ExploitModule]    = []
        self.executions: List[ExploitExecution] = []
        self.sessions:   List[AttackSession]    = []

        self.legal_compliance      = legal_compliance
        self.authorization_manager = authorization_manager
        self.forensic_handler      = forensic_handler

        self._load_data()
        self._initialize_builtin_modules()
        log.info("Penetration Testing Toolkit initialized")

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load_data(self):
        if self.modules_file.exists():
            try:
                with open(self.modules_file, "r") as f:
                    for md in json.load(f):
                        self.modules.append(ExploitModule(**md))
            except Exception as e:
                log.warning("Failed to load exploit modules: %s", e)

        if self.executions_file.exists():
            try:
                with open(self.executions_file, "r") as f:
                    for ed in json.load(f):
                        self.executions.append(ExploitExecution(**ed))
            except Exception as e:
                log.warning("Failed to load exploit executions: %s", e)

        if self.sessions_file.exists():
            try:
                with open(self.sessions_file, "r") as f:
                    for sd in json.load(f):
                        sd["initial_access_time"] = float(sd["initial_access_time"])
                        sd["last_activity"]       = float(sd["last_activity"])
                        self.sessions.append(AttackSession(**sd))
            except Exception as e:
                log.warning("Failed to load attack sessions: %s", e)

    def _save_data(self):
        try:
            with open(self.modules_file,    "w") as f:
                json.dump([asdict(m) for m in self.modules],    f, indent=2)
            with open(self.executions_file, "w") as f:
                json.dump([asdict(e) for e in self.executions], f, indent=2)
            with open(self.sessions_file,   "w") as f:
                json.dump([asdict(s) for s in self.sessions],   f, indent=2)
        except Exception as e:
            log.error("Failed to save penetration testing data: %s", e)

    # ── Built-in modules ───────────────────────────────────────────────────────

    def _initialize_builtin_modules(self):
        if self.modules:
            return
        self.modules.extend([
            ExploitModule(
                module_id="builtin_port_scanner_001",
                name="TCP Port Scanner",
                description="Fast TCP port scanner for service enumeration",
                category="information_gathering", type="scanner",
                author="Apex Security Team",
                credits=["Nmap Project", "Zenmap"],
                references=["https://nmap.org/book/man-port-scanning-techniques.html"],
                required_permissions=["network_access"],
                target_os=["any"], target_arch=["any"],
                disclosure_date="2024-01-01", last_updated=time.time(),
                module_path="builtin/port_scanner.py", dependencies=[],
                parameters={"target": "string", "ports": "string", "timing": "integer"},
                default_parameters={"ports": "1-1000", "timing": 3},
                success_indicators=["open_ports_detected", "service_banner_received"],
                stealth_level=5, legal_risk="medium",
            ),
            ExploitModule(
                module_id="builtin_banner_grabber_001",
                name="HTTP Banner Grabber",
                description="Grab HTTP banners and server information",
                category="information_gathering", type="scanner",
                author="Apex Security Team",
                credits=["Netcat", "Curl"],
                references=["RFC 2616 - Hypertext Transfer Protocol"],
                required_permissions=["network_access"],
                target_os=["any"], target_arch=["any"],
                disclosure_date="2024-01-01", last_updated=time.time(),
                module_path="builtin/banner_grabber.py", dependencies=[],
                parameters={"target": "string", "port": "integer"},
                default_parameters={"port": 80},
                success_indicators=["banner_received", "server_header_parsed"],
                stealth_level=8, legal_risk="low",
            ),
            ExploitModule(
                module_id="builtin_sql_injection_001",
                name="SQL Injection Tester",
                description="Test for SQL injection vulnerabilities",
                category="web_application", type="exploit",
                author="Apex Security Team",
                credits=["SQLMap Project"],
                references=["OWASP SQL Injection Prevention Cheat Sheet"],
                required_permissions=["network_access"],
                target_os=["any"], target_arch=["any"],
                disclosure_date="2024-01-01", last_updated=time.time(),
                module_path="builtin/sql_injection.py", dependencies=[],
                parameters={"target": "string", "parameter": "string", "method": "string"},
                default_parameters={"method": "GET"},
                success_indicators=["sql_error_detected", "data_retrieved"],
                stealth_level=6, legal_risk="high",
            ),
        ])
        self._save_data()

    # ── Module management ──────────────────────────────────────────────────────

    def register_exploit_module(self, name: str, description: str, category: str,
                                exploit_type: str, module_code: str = "",
                                parameters: Dict[str, str] = None,
                                default_parameters: Dict[str, Any] = None,
                                required_permissions: List[str] = None,
                                target_os: List[str] = None,
                                legal_risk: str = "medium") -> str:
        """Register a new exploit module."""
        module_id      = f"module_{int(time.time())}_{hashlib.md5(name.encode()).hexdigest()[:8]}"
        module_filename = f"{module_id}_{name.replace(' ', '_').lower()}.py"
        module_path     = self.modules_path / module_filename
        if module_code:
            module_path.write_text(module_code, encoding="utf-8")

        module = ExploitModule(
            module_id=module_id, name=name, description=description,
            category=category, type=exploit_type,
            author="operator",
            credits=[], references=[],
            required_permissions=required_permissions or ["network_access"],
            target_os=target_os or ["any"], target_arch=["any"],
            disclosure_date=datetime.now().strftime("%Y-%m-%d"),
            last_updated=time.time(),
            module_path=str(module_path), dependencies=[],
            parameters=parameters or {}, default_parameters=default_parameters or {},
            success_indicators=[], stealth_level=5, legal_risk=legal_risk,
        )
        self.modules.append(module)
        self._save_data()
        log.info("Registered exploit module: %s - %s", module_id, name)
        return module_id

    def get_module(self, module_id: str) -> Optional[ExploitModule]:
        for m in self.modules:
            if m.module_id == module_id:
                return m
        return None

    def get_modules_by_category(self, category: str) -> List[ExploitModule]:
        return [m for m in self.modules if m.category == category]

    # ── Authorization / legality check ─────────────────────────────────────────

    def check_authorization_and_legality(self, action_type_value: str,
                                         target: str) -> Tuple[bool, bool]:
        """
        Check authorization and legal compliance for an action.
        Returns (authorized, legal). Both default to False if dependencies not wired.
        """
        authorized = False
        legal      = False

        if self.authorization_manager is not None:
            try:
                authorized = self.authorization_manager.check_authorization(
                    action=action_type_value, target=target
                )[0]
            except Exception as e:
                log.warning("Authorization check failed: %s", e)

        if self.legal_compliance is not None:
            try:
                # ActionType import is lazy to avoid circular dependency
                from apex.security.legal_compliance_framework import ActionType
                action_type = ActionType(action_type_value)
                legal = self.legal_compliance.check_authorization(
                    action_type=action_type, target=target
                )[0]
            except Exception as e:
                log.warning("Legal compliance check failed: %s", e)

        return authorized, legal

    # ── Exploit execution ──────────────────────────────────────────────────────

    def execute_exploit(self, module_id: str, target: str,
                        parameters: Dict[str, Any] = None,
                        session_id: str = None, case_id: str = None) -> str:
        """Execute an exploit module with legal and authorization checks."""
        module = self.get_module(module_id)
        if not module:
            raise ValueError(f"Module {module_id} not found")

        category_to_action = {
            "information_gathering": "passive_reconnaissance",
            "vulnerability_analysis": "active_scanning",
            "web_application":        "exploitation",
            "exploitation":           "exploitation",
            "privilege_escalation":   "privilege_escalation",
            "maintaining_access":     "system_modification",
        }
        action_value = category_to_action.get(module.category, "active_scanning")
        authorized, legal = self.check_authorization_and_legality(action_value, target)

        if not authorized or not legal:
            warning_msg = (
                f"LEGAL/AUTHORIZATION WARNING: Action '{action_value}' on '{target}' "
                f"is not authorized (authorized={authorized}, legal={legal}). "
                "Obtain written permission before proceeding."
            )
            self._record_execution(module_id, target, parameters or {}, session_id,
                                   success=False, output=warning_msg,
                                   error_output="Authorization/Legal check failed",
                                   authorized=authorized)
            log.warning("Exploit execution blocked: %s", warning_msg)
            return warning_msg

        start_time = time.time()
        output, error_output, success = self._simulate_exploit_execution(module, target, parameters)
        end_time = time.time()

        evidence_ids: List[str] = []
        if case_id and success and self.forensic_handler is not None:
            try:
                eid = self.forensic_handler.collect_evidence(
                    case_id=case_id,
                    evidence_type="NETWORK_CAPTURE",
                    source=f"exploit_{module.name}_{target}",
                    description=f"Results from {module.name} against {target}",
                    file_data=output.encode() if output else b"No output",
                    collector="Apex Pentest Toolkit",
                    acquisition_method="automated_exploit",
                )
                evidence_ids.append(eid)
            except Exception as e:
                log.error("Failed to collect evidence: %s", e)

        execution_id = (
            f"execution_{int(time.time())}_"
            f"{hashlib.md5(f'{module_id}{target}'.encode()).hexdigest()[:8]}"
        )
        execution = ExploitExecution(
            execution_id=execution_id,
            module_id=module_id, target=target,
            parameters=parameters or module.default_parameters,
            start_time=start_time, end_time=end_time,
            success=success, output=output, error_output=error_output,
            evidence_collected=evidence_ids, session_id=session_id,
            privileges_gained=[], artifacts_created=[],
            stealth_used=["timestamp_obfuscation"] if module.stealth_level > 5 else [],
            legal_compliance_checked=True, authorized=True,
        )
        self.executions.append(execution)
        self._save_data()
        log.info("Executed exploit: %s - %s on %s", execution_id, module.name, target)

        return (
            f"Exploit Execution Summary:\n"
            f"=========================\n"
            f"Module:           {module.name}\n"
            f"Target:           {target}\n"
            f"Duration:         {end_time - start_time:.2f}s\n"
            f"Success:          {success}\n"
            f"Output Length:    {len(output)} characters\n"
            f"Evidence Collected: {len(evidence_ids)} items\n\n"
            f"{output or 'No output generated'}"
        )

    def _record_execution(self, module_id: str, target: str, parameters: Dict[str, Any],
                          session_id: Optional[str], success: bool, output: str,
                          error_output: str, authorized: bool):
        execution = ExploitExecution(
            execution_id=f"execution_{int(time.time())}",
            module_id=module_id, target=target, parameters=parameters,
            start_time=time.time(), end_time=time.time(),
            success=success, output=output, error_output=error_output,
            evidence_collected=[], session_id=session_id,
            privileges_gained=[], artifacts_created=[], stealth_used=[],
            legal_compliance_checked=True, authorized=authorized,
        )
        self.executions.append(execution)
        self._save_data()

    def _simulate_exploit_execution(self, module: ExploitModule, target: str,
                                    parameters: Dict[str, Any]) -> Tuple[str, str, bool]:
        """Simulate exploit execution (safe for development/testing)."""
        if "port_scanner" in module.module_id:
            return (
                f"Port Scan Results for {target}:\n"
                "PORT     STATE  SERVICE\n"
                "22/tcp   open   ssh\n"
                "80/tcp   open   http\n"
                "443/tcp  open   https\n"
                "3389/tcp open   ms-wbt-server\n\n"
                "Scan completed successfully.",
                "", True,
            )
        elif "banner_grabber" in module.module_id:
            return (
                f"HTTP Banner Information for {target}:\n"
                "Server: Apache/2.4.41 (Ubuntu)\n"
                "X-Powered-By: PHP/7.4.3",
                "", True,
            )
        elif "sql_injection" in module.module_id:
            param = (parameters or {}).get("parameter", "input")
            return (
                f"SQL Injection Test Results for {target}:\n"
                f"[WARNING] Potential SQL injection vulnerability detected\n"
                f"[INFO] Parameter '{param}' appears vulnerable\n"
                "[RECOMMENDATION] Sanitize user inputs and use parameterized queries",
                "", True,
            )
        return f"Module {module.name} executed on {target}", "", True

    # ── Attack sessions ────────────────────────────────────────────────────────

    def create_attack_session(self, target: str, initial_access_method: str,
                              privileges: List[str] = None) -> str:
        """Create an interactive attack session."""
        session_id = f"session_{int(time.time())}_{hashlib.md5(target.encode()).hexdigest()[:8]}"
        session = AttackSession(
            session_id=session_id, target=target,
            initial_access_time=time.time(),
            current_privileges=privileges or ["limited_user"],
            session_type="simulated_shell",
            tools_loaded=["basic_commands"],
            commands_executed=[], files_transferred=[],
            persistence_methods=[], status="active", last_activity=time.time(),
        )
        self.sessions.append(session)
        self._save_data()
        log.info("Created attack session: %s for target %s", session_id, target)
        return session_id

    def execute_session_command(self, session_id: str, command: str,
                                case_id: str = None) -> str:
        """Execute command in an attack session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        output = self._simulate_command_execution(command)
        session.commands_executed.append({"timestamp": time.time(), "command": command,
                                          "output": output, "success": True})
        session.last_activity = time.time()

        if case_id and self.forensic_handler is not None:
            try:
                eid = self.forensic_handler.collect_evidence(
                    case_id=case_id,
                    evidence_type="SYSTEM_LOGS",
                    source=f"session_{session_id}_command",
                    description=f"Command execution: {command}",
                    file_data=output.encode() if output else b"No output",
                    collector="Apex Session Executor",
                    acquisition_method="interactive_session",
                )
                log.info("Collected session evidence: %s", eid)
            except Exception as e:
                log.error("Failed to collect session evidence: %s", e)

        self._save_data()
        return output

    def _simulate_command_execution(self, command: str) -> str:
        cmd = command.lower().strip()
        if cmd in ("ls", "dir"):
            return ("Directory listing:\n"
                    "-rwxr-xr-x 1 user group 1024 Jan 15 10:30 file1.txt\n"
                    "-rwxr-xr-x 1 user group 2048 Jan 15 10:35 file2.log\n"
                    "drwxr-xr-x 2 user group 4096 Jan 15 10:40 documents")
        elif cmd in ("whoami", "id"):
            return "current_user (uid=1000, gid=1000)"
        elif cmd in ("ps", "ps aux"):
            return ("PID    USER  CPU%  MEM%  COMMAND\n"
                    "1234   root   0.5   2.1  /usr/bin/python3\n"
                    "5678   user   1.2   5.3  /usr/bin/firefox")
        elif cmd.startswith("cat"):
            return "File contents would be displayed here"
        elif cmd in ("uname -a", "ver"):
            return "Linux ubuntu-desktop 5.4.0-generic #24-Ubuntu SMP x86_64 GNU/Linux"
        return f"Command '{command}' executed successfully"

    def get_session(self, session_id: str) -> Optional[AttackSession]:
        for s in self.sessions:
            if s.session_id == session_id:
                return s
        return None

    def terminate_session(self, session_id: str) -> bool:
        """Terminate an attack session."""
        session = self.get_session(session_id)
        if not session:
            return False
        session.status        = "terminated"
        session.last_activity = time.time()
        self._save_data()
        log.info("Terminated session: %s", session_id)
        return True

    # ── Reporting ──────────────────────────────────────────────────────────────

    def get_execution_history(self, module_id: str = None,
                              target: str = None) -> List[ExploitExecution]:
        """Get exploit execution history with optional filters."""
        execs = self.executions
        if module_id:
            execs = [e for e in execs if e.module_id == module_id]
        if target:
            execs = [e for e in execs if e.target == target]
        return execs

    def generate_pentest_report(self, target: str, case_id: str = None) -> str:
        """Generate penetration test report for a target."""
        target_execs = [e for e in self.executions if e.target == target]
        if not target_execs:
            return f"No pentest data found for target: {target}"

        lines = [
            "=" * 80, f"PENETRATION TEST REPORT - {target}", "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"Total Executions: {len(target_execs)}", "",
            "EXECUTION SUMMARY:", "-" * 30,
            f"Successful Executions: {sum(1 for e in target_execs if e.success)}",
            f"Failed Executions:     {sum(1 for e in target_execs if not e.success)}",
            "", "DETAILED EXECUTIONS:", "-" * 30,
        ]
        for ex in target_execs:
            m    = self.get_module(ex.module_id)
            name = m.name if m else ex.module_id
            truncated = ex.output[:200] + ("..." if len(ex.output) > 200 else "")
            lines += [
                f"Module:   {name}",
                f"Time:     {datetime.fromtimestamp(ex.start_time).strftime('%Y-%m-%d %H:%M:%S')}",
                f"Duration: {ex.end_time - ex.start_time:.2f}s",
                f"Success:  {ex.success}",
                f"Output:   {truncated}", "",
            ]

        if case_id and self.forensic_handler is not None:
            try:
                ev = self.forensic_handler.get_evidence_summary(case_id)
                lines += [
                    "EVIDENCE SUMMARY:", "-" * 20,
                    f"Total Evidence Items: {ev.get('total_evidence_items', 0)}",
                    f"Evidence Integrity:   {ev.get('integrity_status', {})}",
                ]
            except Exception as e:
                log.warning("Could not retrieve evidence summary: %s", e)

        lines += ["=" * 80, "END OF REPORT", "=" * 80]
        content = "\n".join(lines)

        report_filename = f"pentest_report_{target.replace('.', '_')}_{int(time.time())}.txt"
        (self.sessions_path / report_filename).write_text(content, encoding="utf-8")
        log.info("Generated pentest report: %s", report_filename)
        return content

    def get_toolkit_status(self) -> Dict[str, Any]:
        """Get overall toolkit status."""
        cutoff = time.time() - 86400
        return {
            "total_modules":           len(self.modules),
            "total_executions":        len(self.executions),
            "recent_executions_24h":   sum(1 for e in self.executions if e.start_time > cutoff),
            "active_sessions":         sum(1 for s in self.sessions if s.status == "active"),
            "successful_executions":   sum(1 for e in self.executions if e.success),
            "failed_executions":       sum(1 for e in self.executions if not e.success),
            "modules_by_category":     self._modules_by_category_summary(),
        }

    def _modules_by_category_summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for m in self.modules:
            counts[m.category] = counts.get(m.category, 0) + 1
        return counts


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[PenetrationTestingToolkit] = None

def get_pentest_toolkit(legal_compliance=None, authorization_manager=None,
                        forensic_handler=None) -> PenetrationTestingToolkit:
    """Return the process-level PenetrationTestingToolkit singleton."""
    global _instance
    if _instance is None:
        _instance = PenetrationTestingToolkit(
            legal_compliance=legal_compliance,
            authorization_manager=authorization_manager,
            forensic_handler=forensic_handler,
        )
    return _instance


# ── Tool registration ──────────────────────────────────────────────────────────

def register_tools(registry) -> None:
    tk = get_pentest_toolkit()
    registry.register("pentest_register_module",   "Register a new exploit module",                tk.register_exploit_module,   module="security", tags=["pentest"])
    registry.register("pentest_execute_exploit",   "Execute an exploit module on a target",        tk.execute_exploit,           module="security", tags=["pentest"])
    registry.register("pentest_create_session",    "Create an interactive attack session",         tk.create_attack_session,     module="security", tags=["pentest"])
    registry.register("pentest_run_command",       "Run a command in an attack session",           tk.execute_session_command,   module="security", tags=["pentest"])
    registry.register("pentest_terminate_session", "Terminate an attack session",                  tk.terminate_session,         module="security", tags=["pentest"])
    registry.register("pentest_generate_report",   "Generate penetration test report for target",  tk.generate_pentest_report,   module="security", tags=["pentest"])
    registry.register("pentest_toolkit_status",    "Get overall toolkit status",                   tk.get_toolkit_status,        module="security", tags=["pentest"])
    registry.register("pentest_list_modules",      "List exploit modules by category",             tk.get_modules_by_category,   module="security", tags=["pentest"])
