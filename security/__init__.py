"""
Apex Security Module
====================
Wires together all security subsystems and exposes a single register_tools()
entry point for the tool registry auto-discovery.

Subsystems
----------
- legal_compliance_framework   Legal compliance gating and authorization scopes
- authorization_manager        Engagement contracts and personnel access control
- forensic_evidence_handler    Chain-of-custody evidence collection
- malware_analysis_sandbox     Safe malware examination environment
- penetration_testing_toolkit  Authorized pentest framework
- security_monitoring_dashboard Network IDS, firewall, and incident tracking
- bug_bounty_automation        Automated web / network vulnerability scanning
"""

from .legal_compliance_framework import get_legal_compliance
from .authorization_manager      import get_authorization_manager
from .forensic_evidence_handler  import get_forensic_handler


def register_tools(registry) -> None:
    """
    Discover and register all security tools into the shared registry.

    Dependencies are wired via constructor injection so no module imports
    another module at the top level (preventing circular imports).
    """
    # Bootstrap the three root-level singletons first
    legal      = get_legal_compliance()
    auth_mgr   = get_authorization_manager(legal_compliance=legal)
    forensic   = get_forensic_handler(authorization_manager=auth_mgr)

    # Register their tools
    from . import legal_compliance_framework
    from . import authorization_manager
    from . import forensic_evidence_handler

    legal_compliance_framework.register_tools(registry)
    authorization_manager.register_tools(registry)
    forensic_evidence_handler.register_tools(registry)

    # Wire dependants and register their tools
    from . import malware_analysis_sandbox
    from . import penetration_testing_toolkit
    from . import security_monitoring_dashboard
    from . import bug_bounty_automation

    from .malware_analysis_sandbox     import get_malware_sandbox
    from .penetration_testing_toolkit  import get_pentest_toolkit

    get_malware_sandbox(forensic_handler=forensic, authorization_manager=auth_mgr)
    get_pentest_toolkit(legal_compliance=legal, authorization_manager=auth_mgr,
                        forensic_handler=forensic)

    malware_analysis_sandbox.register_tools(registry)
    penetration_testing_toolkit.register_tools(registry)
    security_monitoring_dashboard.register_tools(registry)
    bug_bounty_automation.register_tools(registry)
