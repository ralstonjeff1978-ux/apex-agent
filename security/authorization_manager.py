"""
AUTHORIZATION MANAGER - Security Engagement Tracking
====================================================
Manages security engagements, contracts, and authorization scopes.

Features:
- Contract lifecycle management
- Scope definition and enforcement
- Personnel access control
- Engagement tracking and reporting
- Evidence handling protocols
- Multi-client support
"""

import json
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

import yaml

log = logging.getLogger("authorization_manager")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"

def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data")) / "authorization"


# ── Enums ──────────────────────────────────────────────────────────────────────

class EngagementStatus(Enum):
    DRAFT     = "draft"
    APPROVED  = "approved"
    ACTIVE    = "active"
    PAUSED    = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EvidenceHandling(Enum):
    CLIENT_OWNED    = "client_owned"
    THIRD_PARTY     = "third_party"
    LAW_ENFORCEMENT = "law_enforcement"
    FORENSIC_LAB    = "forensic_lab"


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class EngagementContract:
    """Security engagement contract details."""
    contract_id:            str
    client_name:            str
    engagement_type:        str               # pentest, vulnerability_assessment, red_team, etc.
    scope_definition:       Dict[str, Any]    # IP ranges, domains, systems
    authorized_actions:     List[str]         # Action types as strings
    personnel:              List[str]         # Authorized team members
    start_date:             float
    end_date:               float
    budget:                 float
    billing_model:          str               # fixed, hourly, retainer
    reporting_requirements: List[str]
    evidence_handling:      str               # EvidenceHandling enum value
    special_conditions:     List[str]
    legal_approvals:        List[str]         # Required legal signatures
    nda_reference:          str
    status:                 str               # EngagementStatus enum value
    created_at:             float
    updated_at:             float
    contract_document:      str               # Path to contract file
    approval_chain:         List[Dict[str, str]]

@dataclass
class ScopeRestriction:
    """Specific restriction within an engagement scope."""
    restriction_id:     str
    contract_id:        str
    restriction_type:   str           # ip_range, domain, system, port, protocol
    restriction_value:  str
    restriction_action: str           # allow, deny, monitor, alert
    justification:      str
    created_at:         float
    expires_at:         Optional[float]


# ── Manager ────────────────────────────────────────────────────────────────────

class AuthorizationManager:
    """Manages security engagement authorizations."""

    def __init__(self, storage_path: str = None, legal_compliance=None):
        """
        Args:
            storage_path:     Override storage directory. Defaults to config.
            legal_compliance: Injected LegalComplianceFramework instance.
                              When provided, approved contracts automatically
                              create corresponding legal authorization scopes.
        """
        self.storage_path = Path(storage_path) if storage_path else _storage_base()
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.contracts_file     = self.storage_path / "engagement_contracts.json"
        self.restrictions_file  = self.storage_path / "scope_restrictions.json"
        self.activity_log_file  = self.storage_path / "authorization_activity.json"

        self.contracts:     List[EngagementContract]  = []
        self.restrictions:  List[ScopeRestriction]    = []
        self.activity_log:  List[Dict[str, Any]]      = []

        self.legal_compliance = legal_compliance

        self._load_data()
        log.info("Authorization Manager initialized")

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load_data(self):
        if self.contracts_file.exists():
            try:
                with open(self.contracts_file, "r") as f:
                    for cd in json.load(f):
                        cd.setdefault("status", "draft")
                        self.contracts.append(EngagementContract(**cd))
            except Exception as e:
                log.warning("Failed to load contracts: %s", e)

        if self.restrictions_file.exists():
            try:
                with open(self.restrictions_file, "r") as f:
                    for rd in json.load(f):
                        self.restrictions.append(ScopeRestriction(**rd))
            except Exception as e:
                log.warning("Failed to load restrictions: %s", e)

        if self.activity_log_file.exists():
            try:
                with open(self.activity_log_file, "r") as f:
                    self.activity_log = json.load(f)
            except Exception as e:
                log.warning("Failed to load activity log: %s", e)

    def _save_data(self):
        try:
            with open(self.contracts_file, "w") as f:
                json.dump([asdict(c) for c in self.contracts], f, indent=2)

            with open(self.restrictions_file, "w") as f:
                json.dump([asdict(r) for r in self.restrictions], f, indent=2)

            with open(self.activity_log_file, "w") as f:
                json.dump(self.activity_log[-1000:], f, indent=2)  # keep last 1000
        except Exception as e:
            log.error("Failed to save authorization data: %s", e)

    # ── Contract lifecycle ─────────────────────────────────────────────────────

    def create_engagement_contract(self, client_name: str, engagement_type: str,
                                   scope_definition: Dict[str, Any],
                                   authorized_actions: List[str],
                                   personnel: List[str],
                                   start_date: float,
                                   end_date: float,
                                   budget: float = 0.0,
                                   billing_model: str = "fixed",
                                   reporting_requirements: List[str] = None,
                                   evidence_handling: str = "client_owned",
                                   special_conditions: List[str] = None,
                                   nda_reference: str = "",
                                   contract_document: str = "") -> str:
        """Create a new security engagement contract."""
        contract_id = f"contract_{int(time.time())}"
        contract = EngagementContract(
            contract_id=contract_id,
            client_name=client_name,
            engagement_type=engagement_type,
            scope_definition=scope_definition,
            authorized_actions=authorized_actions,
            personnel=personnel,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            billing_model=billing_model,
            reporting_requirements=reporting_requirements or [],
            evidence_handling=evidence_handling,
            special_conditions=special_conditions or [],
            legal_approvals=[],
            nda_reference=nda_reference,
            status="draft",
            created_at=time.time(),
            updated_at=time.time(),
            contract_document=contract_document,
            approval_chain=[],
        )
        self.contracts.append(contract)
        self._save_data()
        self._log_activity("contract_created", {
            "contract_id": contract_id,
            "client": client_name,
            "engagement_type": engagement_type,
        })
        log.info("Created engagement contract: %s for %s", contract_id, client_name)
        return contract_id

    def approve_contract(self, contract_id: str, approver: str,
                         approval_notes: str = "") -> bool:
        """Approve an engagement contract."""
        contract = self.get_contract(contract_id)
        if not contract:
            return False
        contract.status     = "approved"
        contract.updated_at = time.time()
        contract.approval_chain.append({
            "approver":  approver,
            "role":      "contract_approver",
            "timestamp": str(time.time()),
            "notes":     approval_notes,
        })
        self._create_legal_authorization(contract)
        self._save_data()
        self._log_activity("contract_approved", {"contract_id": contract_id, "approver": approver})
        log.info("Approved contract: %s", contract_id)
        return True

    def activate_contract(self, contract_id: str, activator: str = "system") -> bool:
        """Activate an approved contract for active engagement."""
        contract = self.get_contract(contract_id)
        if not contract or contract.status != "approved":
            return False
        contract.status     = "active"
        contract.updated_at = time.time()
        contract.approval_chain.append({
            "approver":  activator,
            "role":      "engagement_activator",
            "timestamp": str(time.time()),
            "notes":     "Engagement activated for active work",
        })
        self._save_data()
        self._log_activity("contract_activated", {"contract_id": contract_id, "activator": activator})
        log.info("Activated contract: %s", contract_id)
        return True

    def _create_legal_authorization(self, contract: EngagementContract):
        """Mirror an approved contract into the legal compliance system (if wired)."""
        if self.legal_compliance is None:
            log.debug("Legal compliance not wired; skipping authorization mirror for %s", contract.contract_id)
            return
        try:
            from apex.security.legal_compliance_framework import ActionType
        except ImportError:
            log.warning("Could not import ActionType; skipping legal authorization for %s", contract.contract_id)
            return

        action_types = []
        for action_str in contract.authorized_actions:
            try:
                action_types.append(ActionType[action_str.upper()])
            except KeyError:
                log.warning("Unknown action type: %s", action_str)

        auth_id = self.legal_compliance.create_authorization(
            client_name=contract.client_name,
            engagement_type=contract.engagement_type,
            authorized_actions=action_types,
            ip_ranges=contract.scope_definition.get("ip_ranges", []),
            domains=contract.scope_definition.get("domains", []),
            systems=contract.scope_definition.get("systems", []),
            start_date=contract.start_date,
            end_date=contract.end_date,
            contract_reference=contract.contract_id,
            special_conditions=contract.special_conditions,
            evidence_handling=contract.evidence_handling,
            reporting_requirements=contract.reporting_requirements,
        )
        log.info("Created legal authorization: %s for contract %s", auth_id, contract.contract_id)

    # ── Queries ────────────────────────────────────────────────────────────────

    def get_contract(self, contract_id: str) -> Optional[EngagementContract]:
        """Return a contract by ID, or None."""
        for c in self.contracts:
            if c.contract_id == contract_id:
                return c
        return None

    def get_active_contracts(self) -> List[EngagementContract]:
        """Return all currently active (time-valid) contracts."""
        now = time.time()
        return [c for c in self.contracts
                if c.status == "active" and c.start_date <= now <= c.end_date]

    def get_client_contracts(self, client_name: str) -> List[EngagementContract]:
        """Return all contracts for a specific client."""
        return [c for c in self.contracts if c.client_name == client_name]

    # ── Authorization checks ───────────────────────────────────────────────────

    def check_authorization(self, action: str, target: str,
                            user: str = "operator") -> Tuple[bool, Optional[str]]:
        """Check if an action on a target is authorized for a user."""
        for contract in self.get_active_contracts():
            if user not in contract.personnel:
                continue
            if action not in contract.authorized_actions:
                continue
            if self._target_in_contract_scope(target, contract):
                return True, contract.contract_id
        return False, None

    def validate_action_against_contracts(self, action: str, target: str,
                                          user: str = "operator") -> Dict[str, Any]:
        """Validate an action against all relevant contracts with detailed feedback."""
        authorized, contract_id = self.check_authorization(action, target, user)
        result: Dict[str, Any] = {
            "authorized":          authorized,
            "contract_id":         contract_id,
            "validation_details":  {},
            "recommendations":     [],
        }
        if not authorized:
            active = self.get_active_contracts()
            user_contracts = [c for c in active if user in c.personnel]
            if user_contracts:
                result["recommendations"].append(
                    "Action not authorized under current contracts. "
                    "Check contract scope definitions or request scope expansion."
                )
            else:
                result["recommendations"].append(
                    "No active contracts found for user. "
                    "Create new engagement contract before proceeding."
                )
        return result

    def _target_in_contract_scope(self, target: str, contract: EngagementContract) -> bool:
        scope      = contract.scope_definition
        ip_ranges  = scope.get("ip_ranges", [])
        domains    = scope.get("domains", [])
        systems    = scope.get("systems", [])

        if any(self._target_in_range(target, r) for r in ip_ranges):
            return True
        if any(d in target for d in domains):
            return True
        if any(s in target for s in systems):
            return True
        # No scope constraints defined → implicitly in scope
        return not (ip_ranges or domains or systems)

    def _target_in_range(self, target: str, ip_range: str) -> bool:
        try:
            import ipaddress
            if "/" in ip_range:
                return ipaddress.ip_address(target) in ipaddress.ip_network(ip_range, strict=False)
            return target == ip_range
        except Exception:
            return target == ip_range

    # ── Scope restrictions ─────────────────────────────────────────────────────

    def add_scope_restriction(self, contract_id: str, restriction_type: str,
                              restriction_value: str, restriction_action: str,
                              justification: str,
                              expires_at: Optional[float] = None) -> str:
        """Add a specific restriction to an engagement scope."""
        restriction_id = f"restriction_{int(time.time())}"
        self.restrictions.append(ScopeRestriction(
            restriction_id=restriction_id,
            contract_id=contract_id,
            restriction_type=restriction_type,
            restriction_value=restriction_value,
            restriction_action=restriction_action,
            justification=justification,
            created_at=time.time(),
            expires_at=expires_at,
        ))
        self._save_data()
        self._log_activity("restriction_added", {
            "restriction_id": restriction_id,
            "contract_id":    contract_id,
            "type":           restriction_type,
            "value":          restriction_value,
        })
        log.info("Added scope restriction: %s", restriction_id)
        return restriction_id

    # ── Reporting ──────────────────────────────────────────────────────────────

    def get_authorization_report(self) -> str:
        """Generate authorization status report."""
        active = self.get_active_contracts()
        lines  = [
            "=" * 70,
            "SECURITY AUTHORIZATION REPORT",
            "=" * 70,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"ACTIVE CONTRACTS: {len(active)}",
            "",
        ]
        for c in active:
            lines += [
                f"Contract: {c.contract_id}",
                f"  Client:    {c.client_name}",
                f"  Type:      {c.engagement_type}",
                f"  Period:    {datetime.fromtimestamp(c.start_date).strftime('%Y-%m-%d')} "
                f"to {datetime.fromtimestamp(c.end_date).strftime('%Y-%m-%d')}",
                f"  Personnel: {', '.join(c.personnel)}",
                f"  Actions:   {', '.join(c.authorized_actions)}",
                f"  Evidence:  {c.evidence_handling}",
                "",
            ]
        lines += [
            f"TOTAL RESTRICTIONS:   {len(self.restrictions)}",
            f"ACTIVITY LOG ENTRIES: {len(self.activity_log)}",
            "=" * 70,
        ]
        return "\n".join(lines)

    # ── Activity log ───────────────────────────────────────────────────────────

    def _log_activity(self, activity_type: str, details: Dict[str, Any]):
        self.activity_log.append({
            "timestamp":     time.time(),
            "activity_type": activity_type,
            "details":       details,
            "user":          "system",
        })


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[AuthorizationManager] = None

def get_authorization_manager(legal_compliance=None) -> AuthorizationManager:
    """Return the process-level AuthorizationManager singleton."""
    global _instance
    if _instance is None:
        _instance = AuthorizationManager(legal_compliance=legal_compliance)
    return _instance


# ── Tool registration ──────────────────────────────────────────────────────────

def register_tools(registry) -> None:
    am = get_authorization_manager()
    registry.register("auth_create_contract",    "Create a security engagement contract",        am.create_engagement_contract,       module="security", tags=["authorization"])
    registry.register("auth_approve_contract",   "Approve an engagement contract",               am.approve_contract,                 module="security", tags=["authorization"])
    registry.register("auth_activate_contract",  "Activate an approved engagement contract",     am.activate_contract,                module="security", tags=["authorization"])
    registry.register("auth_check_authorization","Check if an action is authorized for a user",  am.check_authorization,              module="security", tags=["authorization"])
    registry.register("auth_validate_action",    "Validate action against all active contracts", am.validate_action_against_contracts, module="security", tags=["authorization"])
    registry.register("auth_add_restriction",    "Add a scope restriction to a contract",        am.add_scope_restriction,            module="security", tags=["authorization"])
    registry.register("auth_get_report",         "Generate authorization status report",         am.get_authorization_report,         module="security", tags=["authorization"])
