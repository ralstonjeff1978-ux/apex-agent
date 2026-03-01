"""
LEGAL COMPLIANCE FRAMEWORK - Ethical Security Activity Validator
================================================================
Ensures all security activities comply with laws and permissions.

Features:
- Pre-action legal validation
- Authorization scope enforcement
- Risk assessment and warnings
- Jurisdiction-aware compliance
- Evidence preservation protocols
- Professional conduct guidelines
"""

import json
import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import yaml

log = logging.getLogger("legal_compliance")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"

def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data")) / "legal"


# ── Enums ──────────────────────────────────────────────────────────────────────

class LegalRiskLevel(Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"

class ActionType(Enum):
    PASSIVE_RECON         = "passive_reconnaissance"
    ACTIVE_SCANNING       = "active_scanning"
    EXPLOITATION          = "exploitation"
    PRIVILEGE_ESCALATION  = "privilege_escalation"
    DATA_ACCESS           = "data_access"
    SYSTEM_MODIFICATION   = "system_modification"
    NETWORK_INTERCEPTION  = "network_interception"
    SOCIAL_ENGINEERING    = "social_engineering"


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class LegalWarning:
    """Legal warning before a potentially risky action."""
    warning_id:            str
    timestamp:             float
    action_type:           ActionType
    risk_level:            LegalRiskLevel
    description:           str
    legal_concerns:        List[str]
    required_authorization: List[str]
    potential_penalties:   List[str]
    status:                str           # pending | approved | denied | escalated
    authorized_by:         Optional[str] = None
    authorized_at:         Optional[float] = None
    justification:         Optional[str] = None

@dataclass
class AuthorizationScope:
    """Authorized scope for security activities."""
    scope_id:              str
    client_name:           str
    engagement_type:       str
    authorized_actions:    List[ActionType]
    ip_ranges:             List[str]
    domains:               List[str]
    systems:               List[str]
    start_date:            float
    end_date:              float
    contract_reference:    str
    authorized_personnel:  List[str]
    special_conditions:    List[str]
    evidence_handling:     str
    reporting_requirements: List[str]
    created_at:            float


# ── Framework ──────────────────────────────────────────────────────────────────

class LegalComplianceFramework:
    """Main legal compliance system for ethical security engagements."""

    def __init__(self, storage_path: str = None, operator: str = "operator",
                 jurisdiction: str = "US"):
        """
        Args:
            storage_path: Override storage directory. Defaults to config.
            operator:     Identity of the current operator (injected, not hardcoded).
            jurisdiction: Default legal jurisdiction code (US, EU, UK).
        """
        self.storage_path = Path(storage_path) if storage_path else _storage_base()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.warnings_file          = self.storage_path / "legal_warnings.json"
        self.authorizations_file    = self.storage_path / "authorizations.json"
        self.jurisdiction_rules_file = self.storage_path / "jurisdiction_rules.json"

        self.warnings:           List[LegalWarning]      = []
        self.authorizations:     List[AuthorizationScope] = []
        self.jurisdiction_rules: Dict[str, Dict]          = {}

        self.current_user         = operator
        self.default_jurisdiction = jurisdiction

        self._load_data()
        self._load_jurisdiction_rules()
        log.info("Legal Compliance Framework initialised")

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load_data(self):
        if self.warnings_file.exists():
            try:
                with open(self.warnings_file, "r") as f:
                    for wd in json.load(f):
                        wd["action_type"] = ActionType(wd["action_type"])
                        wd["risk_level"]  = LegalRiskLevel(wd["risk_level"])
                        self.warnings.append(LegalWarning(**wd))
            except Exception as e:
                log.warning("Failed to load warnings: %s", e)

        if self.authorizations_file.exists():
            try:
                with open(self.authorizations_file, "r") as f:
                    for ad in json.load(f):
                        if isinstance(ad["authorized_actions"], list):
                            ad["authorized_actions"] = [ActionType(a) for a in ad["authorized_actions"]]
                        self.authorizations.append(AuthorizationScope(**ad))
            except Exception as e:
                log.warning("Failed to load authorizations: %s", e)

    def _load_jurisdiction_rules(self):
        default_rules = {
            "US": {
                "computer_fraud_abuse_act": "Unauthorized access to computers is illegal",
                "electronic_communications_privacy_act": "Intercepting electronic communications requires permission",
                "digital_millennium_copyright_act": "Circumventing copy protection may violate DMCA",
                "state_laws": "Many states have additional computer crime laws",
            },
            "EU": {
                "gdpr": "Data protection regulations apply to all processing activities",
                "network_security_directive": "Critical infrastructure security requirements",
                "national_laws": "Each member state has specific cybercrime laws",
            },
            "UK": {
                "computer_misuse_act": "Unauthorized access to computer material is illegal",
                "data_protection_act": "GDPR compliance required",
                "investigatory_powers_act": "Surveillance and interception regulations",
            },
        }
        if self.jurisdiction_rules_file.exists():
            try:
                with open(self.jurisdiction_rules_file, "r") as f:
                    self.jurisdiction_rules = json.load(f)
            except Exception:
                self.jurisdiction_rules = default_rules
        else:
            self.jurisdiction_rules = default_rules

    def _save_data(self):
        try:
            warnings_out = []
            for w in self.warnings:
                wd = asdict(w)
                wd["action_type"] = w.action_type.value
                wd["risk_level"]  = w.risk_level.value
                warnings_out.append(wd)
            with open(self.warnings_file, "w") as f:
                json.dump(warnings_out, f, indent=2)

            auths_out = []
            for a in self.authorizations:
                ad = asdict(a)
                ad["authorized_actions"] = [x.value for x in a.authorized_actions]
                auths_out.append(ad)
            with open(self.authorizations_file, "w") as f:
                json.dump(auths_out, f, indent=2)
        except Exception as e:
            log.error("Failed to save legal compliance data: %s", e)

    # ── Authorization checks ───────────────────────────────────────────────────

    def check_authorization(self, action_type: ActionType, target: str = "",
                             context: str = "") -> Tuple[bool, Optional[str]]:
        """Check if an action is authorized. Returns (authorized, scope_id)."""
        now = time.time()
        for auth in self.authorizations:
            if not (auth.start_date <= now <= auth.end_date):
                continue
            if self.current_user not in auth.authorized_personnel:
                continue
            if action_type not in auth.authorized_actions:
                continue
            if not target:
                return True, auth.scope_id
            if self._target_authorized(target, auth):
                return True, auth.scope_id
        return False, None

    def _target_authorized(self, target: str, auth: AuthorizationScope) -> bool:
        for ip_range in auth.ip_ranges:
            if self._target_in_range(target, ip_range):
                return True
        for domain in auth.domains:
            if domain in target:
                return True
        for system in auth.systems:
            if system in target:
                return True
        return not (auth.ip_ranges or auth.domains or auth.systems)

    def _target_in_range(self, target: str, ip_range: str) -> bool:
        try:
            import ipaddress
            if "/" in ip_range:
                return ipaddress.ip_address(target) in ipaddress.ip_network(ip_range, strict=False)
            return target == ip_range
        except Exception:
            return target == ip_range

    # ── Risk assessment ────────────────────────────────────────────────────────

    def assess_legal_risk(self, action_type: ActionType, target: str = "",
                           context: str = "") -> LegalRiskLevel:
        risk_map = {
            ActionType.PASSIVE_RECON:        LegalRiskLevel.LOW,
            ActionType.ACTIVE_SCANNING:      LegalRiskLevel.MEDIUM,
            ActionType.EXPLOITATION:         LegalRiskLevel.HIGH,
            ActionType.PRIVILEGE_ESCALATION: LegalRiskLevel.HIGH,
            ActionType.DATA_ACCESS:          LegalRiskLevel.HIGH,
            ActionType.SYSTEM_MODIFICATION:  LegalRiskLevel.CRITICAL,
            ActionType.NETWORK_INTERCEPTION: LegalRiskLevel.HIGH,
            ActionType.SOCIAL_ENGINEERING:   LegalRiskLevel.HIGH,
        }
        risk = risk_map.get(action_type, LegalRiskLevel.MEDIUM)
        if "internal" in context.lower() and "test" in context.lower():
            if risk == LegalRiskLevel.HIGH:
                risk = LegalRiskLevel.MEDIUM
            elif risk == LegalRiskLevel.CRITICAL:
                risk = LegalRiskLevel.HIGH
        return risk

    # ── Warnings ───────────────────────────────────────────────────────────────

    def generate_warning(self, action_type: ActionType, target: str = "",
                         context: str = "") -> LegalWarning:
        risk       = self.assess_legal_risk(action_type, target, context)
        authorized, _ = self.check_authorization(action_type, target, context)

        legal_concerns: List[str] = []
        penalties:      List[str] = []

        rules = self.jurisdiction_rules.get(self.default_jurisdiction, {})
        if action_type == ActionType.ACTIVE_SCANNING:
            legal_concerns.append(rules.get("computer_fraud_abuse_act", "Unauthorized scanning"))
            penalties.append("Up to 10 years imprisonment, $250K fines (CFAA)")
        elif action_type in (ActionType.EXPLOITATION, ActionType.PRIVILEGE_ESCALATION):
            legal_concerns.append("Computer Fraud and Abuse Act violations")
            penalties.append("Up to 10 years imprisonment, civil liability")
        elif action_type == ActionType.DATA_ACCESS and self.default_jurisdiction == "EU":
            legal_concerns.append("GDPR data protection violations")
            penalties.append("Up to 4% of annual revenue or €20 million fine")

        required_auth: List[str] = []
        if risk in (LegalRiskLevel.MEDIUM, LegalRiskLevel.HIGH, LegalRiskLevel.CRITICAL):
            required_auth += [
                "Written permission from system owner",
                "Defined scope of engagement",
                "Signed contract/agreement",
            ]
        if risk == LegalRiskLevel.CRITICAL:
            required_auth += ["Law enforcement coordination", "Forensic readiness approval"]

        warning = LegalWarning(
            warning_id=f"warn_{int(time.time())}",
            timestamp=time.time(),
            action_type=action_type,
            risk_level=risk,
            description=f"Proposed action: {action_type.value} on {target}",
            legal_concerns=legal_concerns,
            required_authorization=required_auth,
            potential_penalties=penalties,
            status="pending",
        )
        self.warnings.append(warning)
        self._save_data()
        return warning

    def approve_warning(self, warning_id: str, justification: str = "",
                        authorized_by: str = None) -> bool:
        for w in self.warnings:
            if w.warning_id == warning_id:
                w.status        = "approved"
                w.authorized_by = authorized_by or self.current_user
                w.authorized_at = time.time()
                w.justification = justification
                self._save_data()
                return True
        return False

    def deny_warning(self, warning_id: str, reason: str = "") -> bool:
        for w in self.warnings:
            if w.warning_id == warning_id:
                w.status        = "denied"
                w.justification = reason
                self._save_data()
                return True
        return False

    def get_pending_warnings(self) -> List[LegalWarning]:
        return [w for w in self.warnings if w.status == "pending"]

    # ── Authorizations ─────────────────────────────────────────────────────────

    def create_authorization(self, client_name: str, engagement_type: str,
                              authorized_actions: List[ActionType],
                              ip_ranges: List[str] = None,
                              domains: List[str] = None,
                              systems: List[str] = None,
                              start_date: float = None, end_date: float = None,
                              contract_reference: str = "",
                              special_conditions: List[str] = None,
                              evidence_handling: str = "client_owned",
                              reporting_requirements: List[str] = None) -> str:
        if not start_date:
            start_date = time.time()
        if not end_date:
            end_date = start_date + 30 * 24 * 3600

        auth = AuthorizationScope(
            scope_id=f"auth_{int(time.time())}",
            client_name=client_name, engagement_type=engagement_type,
            authorized_actions=authorized_actions,
            ip_ranges=ip_ranges or [], domains=domains or [], systems=systems or [],
            start_date=start_date, end_date=end_date,
            contract_reference=contract_reference,
            authorized_personnel=[self.current_user],
            special_conditions=special_conditions or [],
            evidence_handling=evidence_handling,
            reporting_requirements=reporting_requirements or [],
            created_at=time.time(),
        )
        self.authorizations.append(auth)
        self._save_data()
        log.info("Created authorization: %s for %s", auth.scope_id, client_name)
        return auth.scope_id

    def get_active_authorizations(self) -> List[AuthorizationScope]:
        now = time.time()
        return [a for a in self.authorizations if a.start_date <= now <= a.end_date]

    def format_warning_message(self, warning: LegalWarning) -> str:
        risk_descriptions = {
            LegalRiskLevel.LOW:      "LOW RISK — Minimal legal concerns",
            LegalRiskLevel.MEDIUM:   "MEDIUM RISK — Requires proper authorization",
            LegalRiskLevel.HIGH:     "HIGH RISK — Potential legal violations without permission",
            LegalRiskLevel.CRITICAL: "CRITICAL RISK — Likely illegal without explicit permission",
        }
        lines = [
            "=" * 70,
            "LEGAL WARNING — POTENTIAL VIOLATION DETECTED",
            "=" * 70, "",
            f"Action:     {warning.action_type.value}",
            f"Risk Level: {risk_descriptions.get(warning.risk_level, 'UNKNOWN')}",
            "", "LEGAL CONCERNS:",
        ]
        for c in warning.legal_concerns:
            lines.append(f"  • {c}")
        lines += ["", "REQUIRED AUTHORIZATION:"]
        for r in warning.required_authorization:
            lines.append(f"  • {r}")
        lines += ["", "POTENTIAL PENALTIES:"]
        for p in warning.potential_penalties:
            lines.append(f"  • {p}")
        lines += [
            "", "OPTIONS:",
            "  1. Confirm you have proper authorization to proceed",
            "  2. Cancel this action",
            "  3. Create a formal authorization scope first",
            "", f"Warning ID: {warning.warning_id}", "=" * 70,
        ]
        return "\n".join(lines)

    def get_compliance_status(self) -> Dict[str, Any]:
        active  = self.get_active_authorizations()
        pending = self.get_pending_warnings()
        return {
            "active_authorizations": len(active),
            "pending_warnings":      len(pending),
            "compliance_status":     "COMPLIANT" if not pending else "WARNING",
            "next_expiration":       min((a.end_date for a in active), default=float("inf")),
            "jurisdiction":          self.default_jurisdiction,
        }


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[LegalComplianceFramework] = None

def get_legal_compliance(operator: str = "operator") -> LegalComplianceFramework:
    """Return the process-level LegalComplianceFramework singleton."""
    global _instance
    if _instance is None:
        _instance = LegalComplianceFramework(operator=operator)
    return _instance


# ── Tool registration ──────────────────────────────────────────────────────────

def register_tools(registry) -> None:
    lc = get_legal_compliance()
    registry.register("legal_check_authorization", "Check if an action is legally authorized",    lc.check_authorization,   module="security", tags=["legal"])
    registry.register("legal_assess_risk",         "Assess legal risk level for an action",       lc.assess_legal_risk,     module="security", tags=["legal"])
    registry.register("legal_generate_warning",    "Generate a legal warning for a risky action", lc.generate_warning,      module="security", tags=["legal"])
    registry.register("legal_approve_warning",     "Approve a pending legal warning",             lc.approve_warning,       module="security", tags=["legal"])
    registry.register("legal_compliance_status",   "Get overall legal compliance status",         lc.get_compliance_status, module="security", tags=["legal"])
