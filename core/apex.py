"""
Apex — Main Entry Point
=======================
Bootstraps the full agent ecosystem and wires all modules together.

Modules are loaded with graceful fallback — missing optional dependencies
never crash startup. Each subsystem is available via attributes on the
returned Apex instance.

Quick start
-----------
    from apex.core.apex import create_apex

    apex   = create_apex()
    result = apex.execute_task("Summarise all Python files in C:/projects")
    print(result)

With background systems (dream cycle, network monitoring):
    apex = create_apex(start_background=True)

Wiring order
------------
    config.yaml
        → ToolRegistry.discover()          # all modules self-register
        → VerificationEngine(registry)
        → TaskLedger (singleton)
        → AgentCore(call_ai, registry, verifier)
        → experience_engine
          → self_evolution
            → dream_cycle(experience, evolution)
        → perception hub   (interfaces, if enabled)
        → mobile bridge    (hardware, if enabled)
"""

import importlib
import logging
import threading
from pathlib import Path
from typing import Optional

import yaml

from .ai_bridge           import call_ai
from .agent_core          import AgentCore, create_agent
from .verification_engine import create_verification_engine
from .task_ledger         import TaskLedger, get_ledger
from .tool_registry       import ToolRegistry

log = logging.getLogger("apex")

_CONFIG_PATH = Path(__file__).parent / "config.yaml"


def _load_config() -> dict:
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _try_import(dotted: str):
    """
    Import a dotted module path. Returns (module, True) on success,
    (None, False) on ImportError — never raises.
    """
    try:
        return importlib.import_module(dotted), True
    except ImportError as exc:
        log.warning("Optional module unavailable: %s — %s", dotted, exc)
        return None, False


# ── Apex class ────────────────────────────────────────────────────────────────

class Apex:
    """
    Fully wired Apex agent.

    Attributes:
        registry    ToolRegistry  — all registered tools
        verifier    VerificationEngine
        ledger      TaskLedger    — governance audit trail
        agent       AgentCore     — plan / execute / verify engine
        experience  ExperienceEngine or None
        evolution   SelfEvolution or None
        dreamer     DreamCycle or None
        perception  PerceptionHub or None
        mobile      MobileBridge or None
    """

    def __init__(self, config: dict = None):
        self._cfg = config or _load_config()
        self._bg_threads: list = []

        log.info("Bootstrapping Apex...")

        # ── Core ──────────────────────────────────────────────────────────────
        self.registry = ToolRegistry()
        tool_count    = self.registry.discover()
        log.info("%d tool(s) registered after discovery", tool_count)

        self.verifier = create_verification_engine(self.registry)
        self.ledger   = get_ledger()
        self.agent    = create_agent(call_ai, self.registry, self.verifier)

        # ── Learning systems ───────────────────────────────────────────────────
        self.experience: Optional[object] = None
        self.evolution:  Optional[object] = None
        self.dreamer:    Optional[object] = None
        self._wire_learning_systems()

        # ── Optional interface subsystems ──────────────────────────────────────
        self.perception: Optional[object] = None
        self.mobile:     Optional[object] = None
        self._wire_interfaces()

        log.info("Apex ready — %s", self)

    # ── Learning system wiring ─────────────────────────────────────────────────

    def _wire_learning_systems(self):
        """
        Wire experience engine → self-evolution → dream cycle.

        The dream cycle requires both the experience engine (for recording
        lessons and patterns) and the evolution engine (for proposing
        self-improvements). All three are wired or none are.
        """
        if not self._cfg.get("modules", {}).get("memory", True):
            log.info("Memory module disabled in config — learning systems skipped")
            return

        exp_mod,   exp_ok   = _try_import("apex.memory.experience_engine")
        evol_mod,  evol_ok  = _try_import("apex.infrastructure.self_evolution")
        dream_mod, dream_ok = _try_import("apex.memory.dream_cycle")

        if not (exp_ok and evol_ok and dream_ok):
            log.warning("Learning systems partially unavailable — wiring skipped")
            return

        try:
            self.experience = exp_mod.get_experience_engine()
            self.evolution  = evol_mod.get_self_evolution()
            self.dreamer    = dream_mod.get_dream_cycle(self.experience, self.evolution)
            log.info("Learning systems wired: experience → evolution → dream cycle")
        except Exception as exc:
            log.error("Failed to wire learning systems: %s", exc)
            self.experience = self.evolution = self.dreamer = None

    # ── Interface / hardware wiring ────────────────────────────────────────────

    def _wire_interfaces(self):
        """Load the perception hub and mobile bridge if their modules are enabled."""
        modules_cfg = self._cfg.get("modules", {})

        if modules_cfg.get("interfaces", True):
            perc_mod, ok = _try_import("apex.interfaces.enhanced_perception_system")
            if ok:
                try:
                    self.perception = perc_mod.get_perception_system()
                    log.info("Perception hub online")
                except Exception as exc:
                    log.warning("Perception hub failed to initialise: %s", exc)

        if modules_cfg.get("hardware", True):
            mob_mod, ok = _try_import("apex.hardware.mobile_bridge")
            if ok:
                try:
                    self.mobile = mob_mod.get_mobile_bridge()
                    log.info("Mobile bridge ready")
                except Exception as exc:
                    log.warning("Mobile bridge failed to initialise: %s", exc)

    # ── Background subsystem startup ───────────────────────────────────────────

    def start_background_systems(self):
        """
        Start long-running subsystems in daemon background threads.

        Called automatically when create_apex(start_background=True).
        Safe to call manually after the fact.

        Systems started:
        - Dream cycle  (if wired and enabled in config agent.dream_cycle_enabled)
        - Network monitoring (if perception hub is up and agent.network_monitoring)
        - Mobile bridge WebSocket server (if hardware module up and agent.mobile_bridge_autostart)
        """
        agent_cfg = self._cfg.get("agent", {})

        if self.dreamer and agent_cfg.get("dream_cycle_enabled", True):
            t = threading.Thread(
                target=self.dreamer.run_dream_cycle,
                args=(call_ai,),
                name="apex-dream-cycle",
                daemon=True,
            )
            t.start()
            self._bg_threads.append(t)
            log.info("Dream cycle started in background thread")

        if self.perception and agent_cfg.get("network_monitoring", True):
            try:
                self.perception.start_network_monitoring()
                log.info("Network monitoring started")
            except Exception as exc:
                log.warning("Network monitoring failed to start: %s", exc)

        if self.mobile and agent_cfg.get("mobile_bridge_autostart", False):
            mob_mod, ok = _try_import("apex.hardware.mobile_bridge")
            if ok:
                try:
                    mob_mod.start_mobile_bridge()
                    log.info("Mobile bridge WebSocket server started")
                except Exception as exc:
                    log.warning("Mobile bridge server failed to start: %s", exc)

    # ── Public API ─────────────────────────────────────────────────────────────

    def execute_task(self, description: str) -> dict:
        """
        Execute a task through the full plan–execute–verify pipeline.

        Args:
            description: Natural language description of the task.

        Returns:
            Execution summary dict (success, evidence, results, errors).
        """
        return self.agent.execute_task(description)

    def status(self) -> dict:
        """Return a snapshot of every subsystem's availability."""
        return {
            "tools_registered":  len(self.registry._tools),
            "tools_enabled":     sum(1 for t in self.registry._tools.values() if t.enabled),
            "learning_active":   self.experience is not None,
            "perception_active": self.perception is not None,
            "mobile_active":     self.mobile is not None,
            "ledger_session":    self.ledger._session_id if self.ledger else None,
            "bg_threads":        len(self._bg_threads),
        }

    def __repr__(self) -> str:
        s = self.status()
        return (
            f"<Apex tools={s['tools_registered']} "
            f"learning={'on' if s['learning_active'] else 'off'} "
            f"perception={'on' if s['perception_active'] else 'off'}>"
        )


# ── Singleton ─────────────────────────────────────────────────────────────────

_instance: Optional[Apex] = None


def get_apex() -> Apex:
    """Return the process-level Apex singleton, creating it on first call."""
    global _instance
    if _instance is None:
        _instance = Apex()
    return _instance


# ── Factory ───────────────────────────────────────────────────────────────────

def create_apex(start_background: bool = False) -> Apex:
    """
    Bootstrap and return a fully wired Apex agent.

    Args:
        start_background: If True, immediately start dream cycle and
                          network monitoring in background threads.
                          Default False — call start_background_systems()
                          manually when your process is ready.

    Returns:
        Apex instance ready to execute tasks.

    Example:
        apex   = create_apex()
        result = apex.execute_task("List all Python files in C:/projects")
        print(result["evidence"])
    """
    apex = Apex()
    if start_background:
        apex.start_background_systems()
    return apex
