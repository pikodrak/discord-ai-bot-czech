"""
Discord AI Bot Package

This package contains the core bot functionality, including:
- AI provider integrations
- Command handlers (cogs)
- Utility functions
- Context management
- Interest filtering
"""

from bot.context_manager import ContextManager, ConversationWindow, MessageContext
from bot.interest_filter import InterestFilter

__version__ = "1.0.0"
__author__ = "AI Company"
__description__ = "Discord bot with multi-AI provider support"

__all__ = [
    "ContextManager",
    "ConversationWindow",
    "MessageContext",
    "InterestFilter",
]
