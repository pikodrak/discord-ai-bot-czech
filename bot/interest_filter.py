"""
Interest Filter for Discord Messages

This module determines whether the bot should respond to a message based on
various criteria including mentions, keywords, conversation context, and
configurable thresholds.
"""

import logging
import re
from typing import List, Optional, Set

import discord

logger = logging.getLogger(__name__)


class InterestFilter:
    """
    Determines if the bot should respond to a message.

    The filter considers multiple factors:
    - Direct mentions of the bot
    - Replies to bot messages
    - Presence of keywords/triggers
    - Message patterns (questions, etc.)
    - Conversation context
    """

    def __init__(
        self,
        bot_user_id: Optional[int] = None,
        response_threshold: float = 0.6,
        keywords: Optional[List[str]] = None,
        always_respond_in_dms: bool = True
    ):
        """
        Initialize the interest filter.

        Args:
            bot_user_id: Discord user ID of the bot
            response_threshold: Threshold score (0.0-1.0) for responding
            keywords: List of keywords that trigger responses
            always_respond_in_dms: Whether to always respond in DMs
        """
        self.bot_user_id = bot_user_id
        self.response_threshold = response_threshold
        self.keywords = set(keywords or [])
        self.always_respond_in_dms = always_respond_in_dms

        # Default keywords for Czech language
        self.default_czech_keywords = {
            "bot", "ai", "asistent", "pomoc", "help",
            "prosím", "prosim", "děkuji", "dekuji"
        }

        logger.info(
            f"InterestFilter initialized with threshold {response_threshold}, "
            f"{len(self.keywords)} custom keywords"
        )

    def should_respond(
        self,
        message: discord.Message,
        is_reply_to_bot: bool = False,
        conversation_context: Optional[List[str]] = None
    ) -> tuple[bool, float, str]:
        """
        Determine if the bot should respond to a message.

        Args:
            message: Discord message to evaluate
            is_reply_to_bot: Whether message is a reply to the bot
            conversation_context: Recent message contents for context

        Returns:
            Tuple of (should_respond, confidence_score, reason)
        """
        # Ignore bot's own messages
        if message.author.bot and message.author.id == self.bot_user_id:
            return False, 0.0, "own_message"

        # Always respond to DMs if configured
        if isinstance(message.channel, discord.DMChannel):
            if self.always_respond_in_dms:
                return True, 1.0, "direct_message"

        # Calculate interest score
        score = 0.0
        reasons = []

        # 1. Direct mention (highest priority)
        if self.bot_user_id and message.mentions:
            bot_mentioned = any(
                user.id == self.bot_user_id for user in message.mentions
            )
            if bot_mentioned:
                score += 0.5
                reasons.append("mentioned")

        # 2. Reply to bot's message
        if is_reply_to_bot:
            score += 0.4
            reasons.append("reply_to_bot")

        # 3. Check for keywords
        keyword_score = self._check_keywords(message.content)
        if keyword_score > 0:
            score += keyword_score
            reasons.append("keywords")

        # 4. Check if it's a question
        if self._is_question(message.content):
            score += 0.2
            reasons.append("question")

        # 5. Conversation context (if bot recently active)
        if conversation_context:
            context_score = self._check_conversation_context(
                message.content,
                conversation_context
            )
            if context_score > 0:
                score += context_score
                reasons.append("conversation_context")

        # 6. Message length and quality
        quality_score = self._evaluate_message_quality(message.content)
        score += quality_score

        # Cap score at 1.0
        score = min(score, 1.0)

        # Determine if we should respond
        should_respond = score >= self.response_threshold

        reason = ", ".join(reasons) if reasons else "no_triggers"

        logger.debug(
            f"Interest filter result for message {message.id}: "
            f"score={score:.2f}, threshold={self.response_threshold}, "
            f"respond={should_respond}, reason={reason}"
        )

        return should_respond, score, reason

    def _check_keywords(self, content: str) -> float:
        """
        Check if message contains trigger keywords.

        Args:
            content: Message content

        Returns:
            Score contribution from keywords (0.0 to 0.3)
        """
        content_lower = content.lower()

        # Check custom keywords
        custom_match = any(kw in content_lower for kw in self.keywords)

        # Check default Czech keywords
        default_match = any(kw in content_lower for kw in self.default_czech_keywords)

        if custom_match:
            return 0.3
        elif default_match:
            return 0.2

        return 0.0

    def _is_question(self, content: str) -> bool:
        """
        Detect if the message is a question.

        Args:
            content: Message content

        Returns:
            True if message appears to be a question
        """
        # Check for question mark
        if "?" in content:
            return True

        # Check for Czech question words
        czech_question_words = [
            "co", "kde", "kdy", "jak", "proč", "proc", "kdo",
            "který", "ktery", "kolik", "jaký", "jaky",
            "můžeš", "muzes", "umíš", "umis"
        ]

        content_lower = content.lower()
        words = content_lower.split()

        if words and words[0] in czech_question_words:
            return True

        return False

    def _check_conversation_context(
        self,
        content: str,
        context: List[str]
    ) -> float:
        """
        Evaluate if message continues active conversation.

        Args:
            content: Current message content
            context: Recent messages in conversation

        Returns:
            Score contribution from context (0.0 to 0.2)
        """
        if not context or len(context) < 2:
            return 0.0

        # Check if recent messages reference similar topics
        # Simple word overlap check
        current_words = set(content.lower().split())
        context_words = set()

        for msg in context[-3:]:  # Check last 3 messages
            context_words.update(msg.lower().split())

        # Calculate word overlap
        if current_words and context_words:
            overlap = len(current_words & context_words)
            overlap_ratio = overlap / len(current_words)

            if overlap_ratio > 0.3:
                return 0.2
            elif overlap_ratio > 0.15:
                return 0.1

        return 0.0

    def _evaluate_message_quality(self, content: str) -> float:
        """
        Evaluate message quality and substance.

        Args:
            content: Message content

        Returns:
            Score contribution from quality (0.0 to 0.1)
        """
        # Very short messages get lower score
        if len(content.strip()) < 5:
            return 0.0

        # Meaningful length messages get bonus
        if len(content.strip()) > 20:
            return 0.1

        return 0.05

    def add_keyword(self, keyword: str) -> None:
        """
        Add a trigger keyword.

        Args:
            keyword: Keyword to add
        """
        self.keywords.add(keyword.lower())
        logger.info(f"Added keyword: {keyword}")

    def remove_keyword(self, keyword: str) -> bool:
        """
        Remove a trigger keyword.

        Args:
            keyword: Keyword to remove

        Returns:
            True if keyword was removed, False if it didn't exist
        """
        keyword_lower = keyword.lower()
        if keyword_lower in self.keywords:
            self.keywords.remove(keyword_lower)
            logger.info(f"Removed keyword: {keyword}")
            return True
        return False

    def get_keywords(self) -> Set[str]:
        """
        Get all configured keywords.

        Returns:
            Set of all keywords
        """
        return self.keywords.copy()

    def set_threshold(self, threshold: float) -> None:
        """
        Update the response threshold.

        Args:
            threshold: New threshold value (0.0 to 1.0)

        Raises:
            ValueError: If threshold is out of range
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        self.response_threshold = threshold
        logger.info(f"Updated response threshold to {threshold}")

    def update_bot_user_id(self, user_id: int) -> None:
        """
        Update the bot's Discord user ID.

        Args:
            user_id: Discord user ID of the bot
        """
        self.bot_user_id = user_id
        logger.info(f"Updated bot user ID to {user_id}")
