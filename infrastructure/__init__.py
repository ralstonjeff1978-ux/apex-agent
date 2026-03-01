"""
Apex Infrastructure Module
==========================
System infrastructure, deployment, and operations for the Apex agent.
"""

def register_tools(registry) -> None:
    from . import (cloud_sync, docker_deployment, self_improvement,
                   self_evolution, notification_center, backup_recovery_system)
    cloud_sync.register_tools(registry)
    docker_deployment.register_tools(registry)
    self_improvement.register_tools(registry)
    self_evolution.register_tools(registry)
    notification_center.register_tools(registry)
    backup_recovery_system.register_tools(registry)
