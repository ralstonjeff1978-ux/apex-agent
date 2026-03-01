"""
Apex Tools Module
=================
Creative and development tools for the Apex agent.
"""

def register_tools(registry) -> None:
    from . import programming_assistant, book_writing_ai, app_development_assistant, data_annotation_system
    programming_assistant.register_tools(registry)
    book_writing_ai.register_tools(registry)
    app_development_assistant.register_tools(registry)
    data_annotation_system.register_tools(registry)
