"""
Apex Interfaces Module
======================
User interfaces and input/output channels for the Apex agent.
"""

def register_tools(registry) -> None:
    from . import desktop_dashboard, voice_activation, enhanced_perception_system
    desktop_dashboard.register_tools(registry)
    voice_activation.register_tools(registry)
    enhanced_perception_system.register_tools(registry)
