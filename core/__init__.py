"""
Apex Core
=========
Public API for the Apex agent core layer.

All components are wired together here. Import from this package, not from
individual modules, so internal structure can change without breaking callers.

Quick start
-----------
    from core import create_apex

    agent = create_apex()
    result = agent.execute_task("Create a Python hello world script")
    print(result)

Manual wiring (if you need control over each component)
---------------------------------------------------------
    from core import ToolRegistry, call_ai, create_agent, create_verification_engine

    registry = ToolRegistry()
    registry.register("my_tool", "Does a thing", my_fn, module="custom")

    verifier = create_verification_engine(registry)
    agent    = create_agent(call_ai, registry, verifier)
    result   = agent.execute_task("Do the thing")

Authoring tools in submodules
------------------------------
Option A — explicit registration (recommended):

    # apex/memory/__init__.py
    def register_tools(registry):
        from . import store, recall
        registry.register("memory_store",  "Persist a value to memory",   store)
        registry.register("memory_recall", "Retrieve a value from memory", recall)

Option B — decorator:

    # apex/tools/file_ops.py
    from core.tool_registry import tool

    @tool("read_file", "Read a file and return its text", tags=["file"])
    def read_file(path: str) -> str:
        return open(path).read()
"""

import logging
from pathlib import Path

from .ai_bridge           import call_ai
from .agent_core          import AgentCore, TaskPlan, TaskStep, TaskStatus, create_agent
from .verification_engine import (VerificationEngine, VerificationResult,
                                   create_verification_engine)
from .task_ledger         import TaskLedger, LedgerEntry, get_ledger
from .tool_registry       import ToolRegistry, Tool, tool
from .apex                import Apex, create_apex, get_apex

__version__ = "0.1.0"

__all__ = [
    # Bootstrap
    "Apex", "create_apex", "get_apex",
    # AI bridge
    "call_ai",
    # Agent
    "AgentCore", "TaskPlan", "TaskStep", "TaskStatus", "create_agent",
    # Verification
    "VerificationEngine", "VerificationResult", "create_verification_engine",
    # Ledger
    "TaskLedger", "LedgerEntry", "get_ledger",
    # Tools
    "ToolRegistry", "Tool", "tool",
]

log = logging.getLogger("apex.core")
