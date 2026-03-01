"""
FORENSIC EVIDENCE HANDLER - Digital Evidence Management
=======================================================
Professional evidence collection, preservation, and chain of custody.

Features:
- Evidence collection protocols
- Chain of custody tracking
- Hash verification and integrity
- Timestamp synchronization
- Evidence categorization
- Reporting and export
- Legal admissibility preparation
"""

import hashlib
import json
import logging
import os
import shutil
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml

log = logging.getLogger("forensic_evidence")

_CONFIG_PATH = Path(__file__).parent.parent / "core" / "config.yaml"

def _storage_base() -> Path:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return Path(cfg.get("storage", {}).get("base", "C:/ai_agent/apex/data")) / "forensic"


# ── Enums ──────────────────────────────────────────────────────────────────────

class EvidenceType(Enum):
    NETWORK_CAPTURE = "network_capture"
    SYSTEM_LOGS     = "system_logs"
    FILE_SYSTEM     = "file_system"
    MEMORY_DUMP     = "memory_dump"
    SCREENSHOT      = "screenshot"
    DOCUMENT        = "document"
    EMAIL           = "email"
    DATABASE        = "database"
    MOBILE_DEVICE   = "mobile_device"
    CLOUD_ARTIFACT  = "cloud_artifact"

class EvidenceStatus(Enum):
    COLLECTED  = "collected"
    PROCESSING = "processing"
    ANALYZED   = "analyzed"
    REPORTED   = "reported"
    ARCHIVED   = "archived"
    DESTROYED  = "destroyed"


# ── Data models ────────────────────────────────────────────────────────────────

@dataclass
class EvidenceItem:
    """Individual piece of digital evidence."""
    evidence_id:        str
    case_id:            str
    evidence_type:      str
    collection_time:    float
    collector:          str
    source:             str
    description:        str
    file_path:          str
    file_hash:          str
    file_size:          int
    hash_algorithm:     str
    acquisition_method: str
    timestamps:         List[Dict[str, Any]]
    metadata:           Dict[str, Any]
    chain_of_custody:   List[Dict[str, Any]]
    status:             str
    sensitivity_level:  str
    retention_policy:   str
    destruction_date:   Optional[float]

@dataclass
class ChainOfCustodyEntry:
    """Record of evidence custody transfer."""
    transfer_id:       str
    evidence_id:       str
    timestamp:         float
    from_person:       str
    to_person:         str
    reason:            str
    location:          str
    condition:         str
    notes:             str
    digital_signature: str

@dataclass
class EvidenceCase:
    """Case containing multiple evidence items."""
    case_id:              str
    case_name:            str
    client_name:          str
    case_type:            str
    start_date:           float
    end_date:             Optional[float]
    lead_investigator:    str
    team_members:         List[str]
    description:          str
    classification:       str
    evidence_items:       List[str]
    chain_of_custody_log: List[str]
    reports:              List[str]
    status:               str
    created_at:           float


# ── Handler ────────────────────────────────────────────────────────────────────

class ForensicEvidenceHandler:
    """Manages digital evidence collection and preservation."""

    def __init__(self, storage_path: str = None, authorization_manager=None):
        """
        Args:
            storage_path:          Override storage directory. Defaults to config.
            authorization_manager: Optional injected AuthorizationManager instance.
        """
        self.storage_path      = Path(storage_path) if storage_path else _storage_base()
        self.evidence_storage  = self.storage_path / "collected_evidence"
        self.cases_storage     = self.storage_path / "cases"
        self.chain_storage     = self.storage_path / "chain_of_custody"
        self.metadata_storage  = self.storage_path / "metadata"

        for d in (self.evidence_storage, self.cases_storage,
                  self.chain_storage, self.metadata_storage):
            d.mkdir(parents=True, exist_ok=True)

        self.evidence_file = self.storage_path / "evidence_inventory.json"
        self.cases_file    = self.storage_path / "cases.json"
        self.chain_file    = self.storage_path / "custody_chain.json"

        self.evidence_items:  List[EvidenceItem]         = []
        self.cases:           List[EvidenceCase]          = []
        self.chain_entries:   List[ChainOfCustodyEntry]   = []

        self.authorization_manager = authorization_manager

        self._load_data()
        log.info("Forensic Evidence Handler initialised")

    # ── Persistence ────────────────────────────────────────────────────────────

    def _load_data(self):
        if self.evidence_file.exists():
            try:
                with open(self.evidence_file, "r") as f:
                    for item_data in json.load(f):
                        self.evidence_items.append(EvidenceItem(**item_data))
            except Exception as e:
                log.warning("Failed to load evidence inventory: %s", e)

        if self.cases_file.exists():
            try:
                with open(self.cases_file, "r") as f:
                    for case_data in json.load(f):
                        self.cases.append(EvidenceCase(**case_data))
            except Exception as e:
                log.warning("Failed to load cases: %s", e)

        if self.chain_file.exists():
            try:
                with open(self.chain_file, "r") as f:
                    for entry_data in json.load(f):
                        self.chain_entries.append(ChainOfCustodyEntry(**entry_data))
            except Exception as e:
                log.warning("Failed to load custody chain: %s", e)

    def _save_data(self):
        try:
            with open(self.evidence_file, "w") as f:
                json.dump([asdict(i) for i in self.evidence_items], f, indent=2)
            with open(self.cases_file, "w") as f:
                json.dump([asdict(c) for c in self.cases], f, indent=2)
            with open(self.chain_file, "w") as f:
                json.dump([asdict(e) for e in self.chain_entries], f, indent=2)
        except Exception as e:
            log.error("Failed to save evidence data: %s", e)

    # ── Cases ──────────────────────────────────────────────────────────────────

    def create_case(self, case_name: str, client_name: str, case_type: str,
                    lead_investigator: str, description: str = "",
                    classification: str = "confidential",
                    team_members: List[str] = None) -> str:
        case_id = f"case_{int(time.time())}_{hashlib.md5(case_name.encode()).hexdigest()[:8]}"
        case = EvidenceCase(
            case_id=case_id, case_name=case_name, client_name=client_name,
            case_type=case_type, start_date=time.time(), end_date=None,
            lead_investigator=lead_investigator,
            team_members=team_members or [lead_investigator],
            description=description, classification=classification,
            evidence_items=[], chain_of_custody_log=[], reports=[],
            status="active", created_at=time.time()
        )
        self.cases.append(case)
        self._save_data()
        log.info("Created evidence case: %s — %s", case_id, case_name)
        return case_id

    # ── Evidence collection ────────────────────────────────────────────────────

    def collect_evidence(self, case_id: str, evidence_type: str, source: str,
                         description: str, file_data: bytes = None,
                         file_path: str = None, collector: str = "system",
                         acquisition_method: str = "automated_collection",
                         sensitivity_level: str = "confidential") -> str:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        evidence_id = f"evidence_{int(time.time())}_{hashlib.md5(source.encode()).hexdigest()[:8]}"

        evidence_file_path = None
        file_hash = ""
        file_size = 0

        if file_data:
            evidence_filename = f"{evidence_id}_{source.replace('/', '_').replace(chr(92), '_')}"
            evidence_file_path = self.evidence_storage / evidence_filename
            evidence_file_path.write_bytes(file_data)
            file_size = len(file_data)
            file_hash = self._calculate_hash(file_data)
        elif file_path and Path(file_path).exists():
            source_path = Path(file_path)
            evidence_filename = f"{evidence_id}_{source_path.name}"
            evidence_file_path = self.evidence_storage / evidence_filename
            shutil.copy2(source_path, evidence_file_path)
            file_size = source_path.stat().st_size
            file_hash = self._calculate_file_hash(source_path)

        evidence_item = EvidenceItem(
            evidence_id=evidence_id, case_id=case_id,
            evidence_type=evidence_type, collection_time=time.time(),
            collector=collector, source=source, description=description,
            file_path=str(evidence_file_path) if evidence_file_path else "",
            file_hash=file_hash, file_size=file_size, hash_algorithm="SHA256",
            acquisition_method=acquisition_method,
            timestamps=[{"type": "collection", "timestamp": time.time(),
                         "timezone": "UTC", "source": "system_clock"}],
            metadata={"collector_version": "Apex 1.0",
                      "os_platform": os.name,
                      "collection_tool": "Apex Forensic Handler"},
            chain_of_custody=[], status="collected",
            sensitivity_level=sensitivity_level,
            retention_policy=self._get_retention_policy(evidence_type, case.case_type),
            destruction_date=None
        )

        self.evidence_items.append(evidence_item)
        case.evidence_items.append(evidence_id)

        self._add_custody_entry(
            evidence_id=evidence_id, from_person="system", to_person=collector,
            reason="Initial collection", location="Digital evidence locker",
            condition="Collected and secured",
            notes=f"Evidence collected from {source}"
        )

        self._save_data()
        log.info("Collected evidence: %s for case %s", evidence_id, case_id)
        return evidence_id

    # ── Hashing ────────────────────────────────────────────────────────────────

    def _calculate_hash(self, data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def _calculate_file_hash(self, file_path: Path) -> str:
        h = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

    def _get_retention_policy(self, evidence_type: str, case_type: str) -> str:
        return {
            "pentest":          "90_days",
            "incident_response": "1_year",
            "investigation":    "7_years",
            "litigation":       "permanent_until_case_closed",
        }.get(case_type, "1_year")

    # ── Chain of custody ───────────────────────────────────────────────────────

    def _add_custody_entry(self, evidence_id: str, from_person: str, to_person: str,
                           reason: str, location: str, condition: str, notes: str) -> str:
        transfer_id = (
            f"transfer_{int(time.time())}_"
            f"{hashlib.md5(f'{evidence_id}{to_person}'.encode()).hexdigest()[:8]}"
        )
        entry_data = f"{transfer_id}|{evidence_id}|{from_person}|{to_person}|{reason}|{location}|{condition}|{notes}"
        signature  = hashlib.sha256(entry_data.encode()).hexdigest()

        entry = ChainOfCustodyEntry(
            transfer_id=transfer_id, evidence_id=evidence_id,
            timestamp=time.time(), from_person=from_person, to_person=to_person,
            reason=reason, location=location, condition=condition,
            notes=notes, digital_signature=signature
        )
        self.chain_entries.append(entry)

        item = self.get_evidence(evidence_id)
        if item:
            item.chain_of_custody.append(transfer_id)

        case = self.get_case_for_evidence(evidence_id)
        if case:
            case.chain_of_custody_log.append(transfer_id)

        self._save_data()
        log.info("Added custody entry: %s for evidence %s", transfer_id, evidence_id)
        return transfer_id

    def transfer_evidence_custody(self, evidence_id: str, from_person: str,
                                  to_person: str, reason: str,
                                  location: str = "Digital evidence locker",
                                  condition: str = "Good", notes: str = "") -> str:
        item = self.get_evidence(evidence_id)
        if not item:
            raise ValueError(f"Evidence {evidence_id} not found")

        if item.chain_of_custody:
            last = self.get_custody_entry(item.chain_of_custody[-1])
            if last and last.to_person != from_person:
                raise ValueError(f"Evidence not currently in possession of {from_person}")

        transfer_id = self._add_custody_entry(
            evidence_id=evidence_id, from_person=from_person, to_person=to_person,
            reason=reason, location=location, condition=condition, notes=notes
        )
        log.info("Evidence custody transferred: %s from %s to %s",
                 evidence_id, from_person, to_person)
        return transfer_id

    # ── Lookups ────────────────────────────────────────────────────────────────

    def get_evidence(self, evidence_id: str) -> Optional[EvidenceItem]:
        return next((e for e in self.evidence_items if e.evidence_id == evidence_id), None)

    def get_case(self, case_id: str) -> Optional[EvidenceCase]:
        return next((c for c in self.cases if c.case_id == case_id), None)

    def get_case_for_evidence(self, evidence_id: str) -> Optional[EvidenceCase]:
        item = self.get_evidence(evidence_id)
        return self.get_case(item.case_id) if item else None

    def get_custody_entry(self, transfer_id: str) -> Optional[ChainOfCustodyEntry]:
        return next((e for e in self.chain_entries if e.transfer_id == transfer_id), None)

    # ── Integrity ──────────────────────────────────────────────────────────────

    def verify_evidence_integrity(self, evidence_id: str) -> Dict[str, Any]:
        item = self.get_evidence(evidence_id)
        if not item:
            return {"verified": False, "error": "Evidence not found"}
        if not item.file_path or not Path(item.file_path).exists():
            return {"verified": False, "error": "Evidence file not found"}

        current_hash = self._calculate_file_hash(Path(item.file_path))
        return {
            "verified":     current_hash == item.file_hash,
            "stored_hash":  item.file_hash,
            "current_hash": current_hash,
            "file_size":    item.file_size,
            "last_verified": time.time(),
        }

    # ── Reporting ──────────────────────────────────────────────────────────────

    def generate_evidence_report(self, case_id: str, format_type: str = "txt") -> str:
        case = self.get_case(case_id)
        if not case:
            raise ValueError(f"Case {case_id} not found")

        evidence_details = []
        for eid in case.evidence_items:
            ev = self.get_evidence(eid)
            if ev:
                integrity = self.verify_evidence_integrity(eid)
                evidence_details.append({
                    "id":                ev.evidence_id,
                    "type":              ev.evidence_type,
                    "source":            ev.source,
                    "description":       ev.description,
                    "collection_time":   datetime.fromtimestamp(ev.collection_time).isoformat(),
                    "collector":         ev.collector,
                    "file_size":         ev.file_size,
                    "integrity_verified": integrity["verified"],
                    "chain_of_custody_count": len(ev.chain_of_custody),
                })

        content      = self._format_evidence_report(case, evidence_details)
        report_path  = self.cases_storage / f"evidence_report_{case_id}_{int(time.time())}.{format_type}"
        report_path.write_text(content, encoding="utf-8")

        case.reports.append(str(report_path))
        self._save_data()

        log.info("Generated evidence report: %s", report_path.name)
        return str(report_path)

    def _format_evidence_report(self, case: EvidenceCase,
                                 evidence_details: List[Dict]) -> str:
        lines = [
            "=" * 80, "DIGITAL EVIDENCE REPORT", "=" * 80, "",
            f"CASE ID:           {case.case_id}",
            f"CASE NAME:         {case.case_name}",
            f"CLIENT:            {case.client_name}",
            f"CASE TYPE:         {case.case_type}",
            f"LEAD INVESTIGATOR: {case.lead_investigator}",
            f"REPORT DATE:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "", "EVIDENCE ITEMS:", "-" * 40,
        ]
        for ev in evidence_details:
            lines += [
                f"Evidence ID: {ev['id']}",
                f"  Type:       {ev['type']}",
                f"  Source:     {ev['source']}",
                f"  Description:{ev['description']}",
                f"  Collected:  {ev['collection_time']}",
                f"  Collector:  {ev['collector']}",
                f"  Size:       {ev['file_size']} bytes",
                f"  Integrity:  {'VERIFIED' if ev['integrity_verified'] else 'FAILED'}",
                f"  CoC Entries:{ev['chain_of_custody_count']}",
                "",
            ]
        total_coc = sum(len(self.get_evidence(eid).chain_of_custody)
                        for eid in case.evidence_items
                        if self.get_evidence(eid))
        lines += [
            "CHAIN OF CUSTODY SUMMARY:", "-" * 40,
            f"Total custody transfers: {total_coc}", "",
            "=" * 80, "END OF REPORT", "=" * 80,
        ]
        return "\n".join(lines)

    def get_evidence_summary(self, case_id: str) -> Dict[str, Any]:
        case = self.get_case(case_id)
        if not case:
            return {"error": f"Case {case_id} not found"}

        summary: Dict[str, Any] = {
            "case_id":           case_id,
            "case_name":         case.case_name,
            "total_evidence_items": len(case.evidence_items),
            "evidence_by_type":  {},
            "integrity_status":  {"verified": 0, "failed": 0, "unchecked": 0},
            "custody_transfers": 0,
        }
        for eid in case.evidence_items:
            ev = self.get_evidence(eid)
            if ev:
                summary["evidence_by_type"][ev.evidence_type] = (
                    summary["evidence_by_type"].get(ev.evidence_type, 0) + 1
                )
                summary["custody_transfers"] += len(ev.chain_of_custody)
                try:
                    result = self.verify_evidence_integrity(eid)
                    key = "verified" if result["verified"] else "failed"
                    summary["integrity_status"][key] += 1
                except Exception:
                    summary["integrity_status"]["unchecked"] += 1

        return summary

    def secure_evidence_storage(self) -> Dict[str, Any]:
        return {
            "total_cases":         len(self.cases),
            "active_cases":        sum(1 for c in self.cases if c.status == "active"),
            "total_evidence_items": len(self.evidence_items),
            "storage_path":        str(self.evidence_storage),
            "storage_size_mb":     self._get_directory_size(self.evidence_storage) / (1024 * 1024),
        }

    def _get_directory_size(self, directory: Path) -> int:
        total = 0
        try:
            for item in directory.rglob("*"):
                if item.is_file():
                    total += item.stat().st_size
        except Exception:
            pass
        return total


# ── Singleton ──────────────────────────────────────────────────────────────────

_instance: Optional[ForensicEvidenceHandler] = None

def get_forensic_handler(authorization_manager=None) -> ForensicEvidenceHandler:
    """Return the process-level ForensicEvidenceHandler singleton."""
    global _instance
    if _instance is None:
        _instance = ForensicEvidenceHandler(authorization_manager=authorization_manager)
    return _instance


# ── Tool registration ──────────────────────────────────────────────────────────

def register_tools(registry) -> None:
    handler = get_forensic_handler()
    registry.register("forensic_create_case",        "Create a new evidence case",               handler.create_case,                  module="security", tags=["forensic"])
    registry.register("forensic_collect_evidence",   "Collect and store digital evidence",       handler.collect_evidence,             module="security", tags=["forensic"])
    registry.register("forensic_transfer_custody",   "Transfer evidence chain of custody",       handler.transfer_evidence_custody,    module="security", tags=["forensic"])
    registry.register("forensic_verify_integrity",   "Verify evidence file hash integrity",      handler.verify_evidence_integrity,    module="security", tags=["forensic"])
    registry.register("forensic_generate_report",    "Generate a formal evidence report",        handler.generate_evidence_report,     module="security", tags=["forensic"])
    registry.register("forensic_get_summary",        "Get evidence summary for a case",          handler.get_evidence_summary,         module="security", tags=["forensic"])
