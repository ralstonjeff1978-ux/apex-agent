"""
Apex Memory Module
==================
Long-term memory, experience tracking, dream-cycle reflection,
and autonomous learning for the Apex agent system.

Sub-modules:
- memory_tools      : Surface/deep storage, decisions, lessons, skills, projects
- experience_engine : Task-level learning and per-tool reputation tracking
- dream_cycle       : Idle-time reflection and insight consolidation
- learning_engine   : Curiosity engine, knowledge gap tracking, hallucination guard
"""


def register_tools(registry) -> None:
    from . import memory_tools, experience_engine, dream_cycle, learning_engine
    memory_tools.register_tools(registry)
    experience_engine.register_tools(registry)
    dream_cycle.register_tools(registry)
    learning_engine.register_tools(registry)
