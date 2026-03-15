"""
Context Manager for Discord Conversations

This module manages conversation context windows per channel/thread,
maintaining message history and providing it to the LLM for context-aware responses.
"""

import logging
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Deque, Dict, List, Optional

import discord

logger = logging.getLogger(__name__)


@dataclass
class MessageContext:
    """
    Represents a single message in the conversation context.

    Attributes:
        author_id: Discord user ID of the message author
        author_name: Display name of the author
        content: Message content
        timestamp: When the message was sent
        is_bot: Whether the message is from a bot
        channel_id: Channel where message was sent
    """
    author_id: int
    author_name: str
    content: str
    timestamp: datetime
    is_bot: bool = False
    channel_id: int = 0


@dataclass
class ConversationWindow:
    """
    Manages a conversation window for a specific channel/thread.

    Attributes:
        channel_id: Discord channel ID
        max_messages: Maximum number of messages to keep
        messages: Deque of messages in conversation order
        last_activity: Timestamp of last message
    """
    channel_id: int
    max_messages: int = 50
    messages: Deque[MessageContext] = field(default_factory=deque)
    last_activity: datetime = field(default_factory=datetime.now)

    def add_message(self, message: MessageContext) -> None:
        """
        Add a message to the conversation window.

        Args:
            message: Message to add
        """
        self.messages.append(message)
        self.last_activity = datetime.now()

        # Trim if exceeds max size
        while len(self.messages) > self.max_messages:
            self.messages.popleft()

        logger.debug(
            f"Added message to channel {self.channel_id}. "
            f"Total messages: {len(self.messages)}"
        )

    def get_messages(self, limit: Optional[int] = None) -> List[MessageContext]:
        """
        Get messages from the conversation window.

        Args:
            limit: Optional limit on number of messages to return (most recent)

        Returns:
            List of messages in chronological order
        """
        messages = list(self.messages)
        if limit and limit < len(messages):
            messages = messages[-limit:]
        return messages

    def clear(self) -> None:
        """Clear all messages from the conversation window."""
        self.messages.clear()
        logger.info(f"Cleared conversation window for channel {self.channel_id}")

    def get_summary(self) -> Dict[str, any]:
        """
        Get summary statistics for this conversation window.

        Returns:
            Dictionary containing summary information
        """
        return {
            "channel_id": self.channel_id,
            "message_count": len(self.messages),
            "max_messages": self.max_messages,
            "last_activity": self.last_activity.isoformat(),
            "user_count": len(set(msg.author_id for msg in self.messages)),
        }


class ContextManager:
    """
    Manages conversation contexts across all channels and threads.

    This class maintains separate conversation windows for each channel/thread,
    providing context-aware message history for AI responses.
    """

    def __init__(self, max_messages_per_channel: int = 50):
        """
        Initialize the context manager.

        Args:
            max_messages_per_channel: Maximum messages to keep per channel
        """
        self.max_messages_per_channel = max_messages_per_channel
        self.windows: Dict[int, ConversationWindow] = {}
        logger.info(
            f"ContextManager initialized with max {max_messages_per_channel} "
            f"messages per channel"
        )

    def get_or_create_window(self, channel_id: int) -> ConversationWindow:
        """
        Get existing conversation window or create a new one.

        Args:
            channel_id: Discord channel ID

        Returns:
            ConversationWindow for the specified channel
        """
        if channel_id not in self.windows:
            self.windows[channel_id] = ConversationWindow(
                channel_id=channel_id,
                max_messages=self.max_messages_per_channel
            )
            logger.info(f"Created new conversation window for channel {channel_id}")

        return self.windows[channel_id]

    def add_message(
        self,
        channel_id: int,
        message: discord.Message
    ) -> None:
        """
        Add a Discord message to the conversation context.

        Args:
            channel_id: Discord channel ID
            message: Discord message object
        """
        window = self.get_or_create_window(channel_id)

        # Create message context
        msg_context = MessageContext(
            author_id=message.author.id,
            author_name=message.author.display_name,
            content=message.content,
            timestamp=message.created_at,
            is_bot=message.author.bot,
            channel_id=channel_id
        )

        window.add_message(msg_context)

    def get_context_messages(
        self,
        channel_id: int,
        limit: Optional[int] = None
    ) -> List[MessageContext]:
        """
        Get conversation context for a channel.

        Args:
            channel_id: Discord channel ID
            limit: Optional limit on number of messages

        Returns:
            List of messages in chronological order
        """
        window = self.get_or_create_window(channel_id)
        return window.get_messages(limit=limit)

    def format_for_llm(
        self,
        channel_id: int,
        limit: Optional[int] = None,
        include_bot_messages: bool = True
    ) -> List[Dict[str, str]]:
        """
        Format conversation context for LLM consumption.

        Args:
            channel_id: Discord channel ID
            limit: Optional limit on number of messages
            include_bot_messages: Whether to include bot's own messages

        Returns:
            List of message dictionaries in LLM format (role, content)
        """
        messages = self.get_context_messages(channel_id, limit)

        llm_messages = []
        for msg in messages:
            # Skip bot messages if requested
            if not include_bot_messages and msg.is_bot:
                continue

            # Determine role based on whether it's a bot message
            role = "assistant" if msg.is_bot else "user"

            # Format content with author name for multi-user context
            if role == "user":
                content = f"{msg.author_name}: {msg.content}"
            else:
                content = msg.content

            llm_messages.append({
                "role": role,
                "content": content
            })

        return llm_messages

    def clear_channel(self, channel_id: int) -> None:
        """
        Clear conversation context for a specific channel.

        Args:
            channel_id: Discord channel ID
        """
        if channel_id in self.windows:
            self.windows[channel_id].clear()
        else:
            logger.warning(
                f"Attempted to clear non-existent window for channel {channel_id}"
            )

    def clear_all(self) -> None:
        """Clear all conversation contexts."""
        count = len(self.windows)
        self.windows.clear()
        logger.info(f"Cleared all {count} conversation windows")

    def get_stats(self) -> Dict[str, any]:
        """
        Get statistics about all conversation windows.

        Returns:
            Dictionary containing overall statistics
        """
        total_messages = sum(len(w.messages) for w in self.windows.values())

        return {
            "total_windows": len(self.windows),
            "total_messages": total_messages,
            "max_messages_per_channel": self.max_messages_per_channel,
            "windows": {
                cid: window.get_summary()
                for cid, window in self.windows.items()
            }
        }

    def cleanup_inactive(self, inactive_hours: int = 24) -> int:
        """
        Remove conversation windows that have been inactive.

        Args:
            inactive_hours: Hours of inactivity before cleanup

        Returns:
            Number of windows removed
        """
        from datetime import timedelta

        cutoff_time = datetime.now() - timedelta(hours=inactive_hours)
        to_remove = []

        for channel_id, window in self.windows.items():
            if window.last_activity < cutoff_time:
                to_remove.append(channel_id)

        for channel_id in to_remove:
            del self.windows[channel_id]

        if to_remove:
            logger.info(
                f"Cleaned up {len(to_remove)} inactive conversation windows "
                f"(inactive for {inactive_hours}+ hours)"
            )

        return len(to_remove)
