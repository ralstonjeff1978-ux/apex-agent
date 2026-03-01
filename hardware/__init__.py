"""
Apex Hardware Module
====================
Hardware bridges and device controllers for the Apex agent.
"""

def register_tools(registry) -> None:
    from . import pico_bridge, ar_glasses_bridge, drone_control, mobile_bridge
    pico_bridge.register_tools(registry)
    ar_glasses_bridge.register_tools(registry)
    drone_control.register_tools(registry)
    mobile_bridge.register_tools(registry)
