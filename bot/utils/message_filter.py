"""
Message Interest Detection Module

This module provides heuristic and AI-based filtering to determine if a message
is interesting enough to respond to. Uses keywords, questions, mentions,
sentiment analysis, and optional AI scoring.
"""

import re
import logging
from typing import Optional, Dict, List, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import defaultdict

import discord

logger = logging.getLogger(__name__)


@dataclass
class MessageScore:
    """
    Score breakdown for a message's interest level.

    Attributes:
        total: Final total score (0.0 to 1.0)
        is_mention: Whether bot was mentioned
        is_question: Whether message is a question
        has_keywords: Whether interesting keywords found
        conversation_context: Score from conversation context
        sentiment_score: Sentiment analysis score
        length_score: Score based on message length
        spam_penalty: Penalty for spam patterns
        details: Additional scoring details
    """
    total: float
    is_mention: bool = False
    is_question: bool = False
    has_keywords: bool = False
    conversation_context: float = 0.0
    sentiment_score: float = 0.0
    length_score: float = 0.0
    spam_penalty: float = 0.0
    details: Dict[str, any] = None

    def __post_init__(self):
        """Initialize details dict if not provided."""
        if self.details is None:
            self.details = {}


class MessageFilter:
    """
    Filter for detecting interesting messages that warrant bot responses.

    Uses multiple heuristics including:
    - Direct mentions
    - Question detection
    - Keyword matching
    - Conversation context
    - Sentiment analysis
    - Spam detection
    - Rate limiting
    """

    # Question patterns for Czech and English
    QUESTION_PATTERNS = [
        r'\?$',  # Ends with question mark
        r'^(co|kdo|kdy|kde|jak|proč|jaký|která|které|který)',  # Czech question words
        r'^(what|who|when|where|why|how|which)',  # English question words
        r'\b(víš|víte|znáš|znáte|myslíš|myslíte)\b',  # Czech "do you know/think"
        r'\b(know|think|believe|suppose)\b.*\?',  # English questions
    ]

    # Keywords that indicate interesting content (Czech + English)
    INTERESTING_KEYWORDS = {
        # Technology
        'ai', 'umělá inteligence', 'python', 'javascript', 'programování',
        'kód', 'code', 'bug', 'error', 'algorithm', 'algoritmus',

        # Discussion starters
        'myslíš', 'myslíte', 'think', 'opinion', 'názor',
        'diskuze', 'debate', 'debata',

        # Help/questions
        'pomoc', 'help', 'nevím', "don't know", 'otázka', 'question',
        'poradit', 'advice', 'suggest',

        # Topics that invite response
        'zajímavé', 'interesting', 'cool', 'amazing', 'skvělé',
    }

    # Conversation starter phrases
    CONVERSATION_STARTERS = [
        r'\b(co si myslíš|co si myslíte)\b',  # what do you think
        r'\b(slyšel jsi|slyšeli jste|heard about)\b',  # heard about
        r'\b(víš něco o|víte něco o|know anything about)\b',  # know about
        r'\b(mám otázku|have a question)\b',  # have a question
        r'\b(co říkáš na|co říkáte na|what do you say about)\b',  # what about
    ]

    # Spam patterns
    SPAM_PATTERNS = [
        r'^(.)\1{10,}$',  # Repeated characters (aaaaaaa)
        r'^[!?]{5,}$',  # Only punctuation
        r'^[A-Z\s!?]{20,}$',  # ALL CAPS LONG MESSAGE
        r'^[\U0001F300-\U0001F9FF]{3,}$',  # Only emojis
    ]

    # Short non-meaningful messages to ignore
    IGNORE_SHORT = {
        'ok', 'lol', 'xd', 'haha', 'ano', 'ne', 'yes', 'no',
        'cool', 'nice', 'wow', 'oof', 'bruh', 'omg', 'wtf',
        'díky', 'thanks', 'thx', 'ty', 'ok', 'k', 'kk',
    }

    def __init__(
        self,
        bot_id: int,
        response_threshold: float = 0.6,
        min_message_length: int = 3,
        max_responses_per_minute: int = 5,
        conversation_context_weight: float = 0.3,
        enable_ai_scoring: bool = False,
    ):
        """
        Initialize message filter.

        Args:
            bot_id: Discord bot user ID
            response_threshold: Minimum score to trigger response (0.0 to 1.0)
            min_message_length: Minimum message length to consider
            max_responses_per_minute: Rate limit for responses
            conversation_context_weight: Weight of conversation context in scoring
            enable_ai_scoring: Whether to use AI for additional scoring
        """
        self.bot_id = bot_id
        self.response_threshold = response_threshold
        self.min_message_length = min_message_length
        self.max_responses_per_minute = max_responses_per_minute
        self.conversation_context_weight = conversation_context_weight
        self.enable_ai_scoring = enable_ai_scoring

        # Compile regex patterns
        self._question_regex = [re.compile(p, re.IGNORECASE) for p in self.QUESTION_PATTERNS]
        self._starter_regex = [re.compile(p, re.IGNORECASE) for p in self.CONVERSATION_STARTERS]
        self._spam_regex = [re.compile(p) for p in self.SPAM_PATTERNS]

        # Track recent responses for rate limiting
        self._recent_responses: Dict[int, List[datetime]] = defaultdict(list)

        # Track conversation context
        self._conversation_history: Dict[int, List[Dict]] = defaultdict(list)
        self._max_history_per_channel = 20

        logger.info(
            f"MessageFilter initialized: threshold={response_threshold}, "
            f"ai_scoring={enable_ai_scoring}"
        )

    async def is_interesting(
        self,
        message: discord.Message,
        context_messages: Optional[List[discord.Message]] = None,
    ) -> tuple[bool, MessageScore]:
        """
        Determine if a message is interesting enough to respond to.

        Args:
            message: Discord message to evaluate
            context_messages: Optional recent messages for context

        Returns:
            Tuple of (should_respond, score_breakdown)
        """
        # Quick rejection filters
        if not self._should_process_message(message):
            return False, MessageScore(total=0.0, details={'reason': 'filtered_out'})

        # Check rate limiting
        if not self._check_rate_limit(message.channel.id):
            return False, MessageScore(total=0.0, details={'reason': 'rate_limited'})

        # Calculate interest score
        score = await self._calculate_interest_score(message, context_messages)

        # Determine if should respond
        should_respond = score.total >= self.response_threshold

        if should_respond:
            logger.info(
                f"Message deemed interesting: score={score.total:.2f}, "
                f"channel={message.channel.name}, author={message.author.name}"
            )
            self._record_response(message.channel.id)
        else:
            logger.debug(
                f"Message filtered: score={score.total:.2f} < {self.response_threshold}"
            )

        return should_respond, score

    def _should_process_message(self, message: discord.Message) -> bool:
        """
        Quick filters to reject messages without scoring.

        Args:
            message: Discord message

        Returns:
            True if message should be processed
        """
        # Ignore bot messages
        if message.author.bot:
            return False

        # Ignore system messages
        if message.type != discord.MessageType.default:
            return False

        # Ignore very short messages
        if len(message.content.strip()) < self.min_message_length:
            return False

        # Ignore common short non-meaningful messages
        content_lower = message.content.strip().lower()
        if content_lower in self.IGNORE_SHORT:
            return False

        return True

    async def _calculate_interest_score(
        self,
        message: discord.Message,
        context_messages: Optional[List[discord.Message]] = None,
    ) -> MessageScore:
        """
        Calculate comprehensive interest score for a message.

        Args:
            message: Discord message to score
            context_messages: Optional context messages

        Returns:
            MessageScore with breakdown
        """
        content = message.content.strip()
        score_components = {}

        # Check for direct mention (highest priority)
        is_mention = any(mention.id == self.bot_id for mention in message.mentions)
        if is_mention:
            score_components['mention'] = 1.0

        # Check if message is a question
        is_question = self._is_question(content)
        if is_question:
            score_components['question'] = 0.7

        # Check for interesting keywords
        has_keywords, keyword_score = self._check_keywords(content)
        if has_keywords:
            score_components['keywords'] = keyword_score

        # Check for conversation starters
        is_starter = self._is_conversation_starter(content)
        if is_starter:
            score_components['conversation_starter'] = 0.6

        # Analyze message length and quality
        length_score = self._score_message_length(content)
        score_components['length'] = length_score

        # Check for spam patterns (negative score)
        spam_penalty = self._check_spam(content)
        if spam_penalty > 0:
            score_components['spam_penalty'] = -spam_penalty

        # Analyze conversation context
        context_score = self._analyze_context(message, context_messages)
        if context_score > 0:
            score_components['context'] = context_score

        # Sentiment analysis (basic heuristic)
        sentiment_score = self._analyze_sentiment(content)
        score_components['sentiment'] = sentiment_score

        # Calculate total score
        total_score = self._calculate_total_score(score_components)

        # Cap between 0.0 and 1.0
        total_score = max(0.0, min(1.0, total_score))

        return MessageScore(
            total=total_score,
            is_mention=is_mention,
            is_question=is_question,
            has_keywords=has_keywords,
            conversation_context=context_score,
            sentiment_score=sentiment_score,
            length_score=length_score,
            spam_penalty=spam_penalty,
            details=score_components,
        )

    def _is_question(self, content: str) -> bool:
        """Check if message is a question."""
        return any(regex.search(content) for regex in self._question_regex)

    def _is_conversation_starter(self, content: str) -> bool:
        """Check if message is a conversation starter."""
        return any(regex.search(content) for regex in self._starter_regex)

    def _check_keywords(self, content: str) -> tuple[bool, float]:
        """
        Check for interesting keywords.

        Returns:
            Tuple of (has_keywords, score)
        """
        content_lower = content.lower()
        matched_keywords = [
            kw for kw in self.INTERESTING_KEYWORDS
            if kw in content_lower
        ]

        if not matched_keywords:
            return False, 0.0

        # Score based on number and relevance of keywords
        score = min(0.8, len(matched_keywords) * 0.2)
        return True, score

    def _check_spam(self, content: str) -> float:
        """
        Check for spam patterns.

        Returns:
            Penalty score (0.0 to 1.0)
        """
        # Check regex patterns
        for regex in self._spam_regex:
            if regex.search(content):
                return 0.8

        # Check for excessive repetition
        words = content.split()
        if len(words) > 3:
            unique_words = set(words)
            repetition_ratio = 1.0 - (len(unique_words) / len(words))
            if repetition_ratio > 0.7:
                return 0.5

        return 0.0

    def _score_message_length(self, content: str) -> float:
        """
        Score message based on length and quality.

        Returns:
            Score (0.0 to 1.0)
        """
        word_count = len(content.split())
        char_count = len(content)

        # Optimal length: 5-50 words
        if word_count < 2:
            return 0.1
        elif word_count <= 5:
            return 0.3
        elif word_count <= 50:
            return 0.5
        elif word_count <= 100:
            return 0.4
        else:
            # Very long messages might be spam or copy-paste
            return 0.2

    def _analyze_sentiment(self, content: str) -> float:
        """
        Basic sentiment analysis using heuristics.

        Returns:
            Sentiment score (-1.0 to 1.0)
        """
        content_lower = content.lower()

        positive_words = {
            'skvělé', 'great', 'awesome', 'cool', 'amazing', 'zajímavé',
            'interesting', 'díky', 'thanks', 'super', 'perfektní', 'perfect',
        }

        negative_words = {
            'špatné', 'bad', 'awful', 'terrible', 'stupid', 'hate',
            'nefunguje', "doesn't work", 'broken', 'bug', 'error',
        }

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        # Normalize to -1.0 to 1.0
        if positive_count + negative_count == 0:
            return 0.0

        sentiment = (positive_count - negative_count) / (positive_count + negative_count)
        return sentiment * 0.3  # Weight sentiment at 30% max

    def _analyze_context(
        self,
        message: discord.Message,
        context_messages: Optional[List[discord.Message]] = None,
    ) -> float:
        """
        Analyze conversation context to determine relevance.

        Args:
            message: Current message
            context_messages: Recent messages in channel

        Returns:
            Context score (0.0 to 1.0)
        """
        if not context_messages:
            return 0.0

        # Check if bot recently participated in conversation
        bot_recent_messages = [
            msg for msg in context_messages[-10:]
            if msg.author.id == self.bot_id
        ]

        if bot_recent_messages:
            # Bot is in active conversation
            last_bot_message = bot_recent_messages[-1]
            time_since_bot = (message.created_at - last_bot_message.created_at).total_seconds()

            # Higher score if message is within 5 minutes of bot's last message
            if time_since_bot < 300:  # 5 minutes
                return 0.6 * self.conversation_context_weight

        # Check if someone replied to the bot
        if message.reference and message.reference.message_id:
            try:
                referenced_msg = next(
                    (msg for msg in context_messages if msg.id == message.reference.message_id),
                    None
                )
                if referenced_msg and referenced_msg.author.id == self.bot_id:
                    return 0.8 * self.conversation_context_weight
            except Exception as e:
                logger.debug(f"Error checking message reference: {e}")

        return 0.0

    def _calculate_total_score(self, components: Dict[str, float]) -> float:
        """
        Calculate total interest score from components.

        Args:
            components: Dictionary of score components

        Returns:
            Total score
        """
        # Mentions are automatic high score
        if components.get('mention', 0) > 0:
            return 1.0

        # Weighted sum of other components
        weights = {
            'question': 0.35,
            'keywords': 0.25,
            'conversation_starter': 0.25,
            'context': 0.20,
            'length': 0.10,
            'sentiment': 0.10,
            'spam_penalty': 1.0,  # Full penalty
        }

        total = 0.0
        for component, value in components.items():
            weight = weights.get(component, 0.1)
            total += value * weight

        return total

    def _check_rate_limit(self, channel_id: int) -> bool:
        """
        Check if bot is within rate limits for a channel.

        Args:
            channel_id: Discord channel ID

        Returns:
            True if within rate limits
        """
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)

        # Clean old entries
        self._recent_responses[channel_id] = [
            timestamp for timestamp in self._recent_responses[channel_id]
            if timestamp > cutoff
        ]

        # Check count
        return len(self._recent_responses[channel_id]) < self.max_responses_per_minute

    def _record_response(self, channel_id: int) -> None:
        """Record that bot responded in a channel."""
        self._recent_responses[channel_id].append(datetime.now())

    def update_configuration(
        self,
        response_threshold: Optional[float] = None,
        max_responses_per_minute: Optional[int] = None,
        enable_ai_scoring: Optional[bool] = None,
    ) -> None:
        """
        Update filter configuration dynamically.

        Args:
            response_threshold: New response threshold
            max_responses_per_minute: New rate limit
            enable_ai_scoring: Enable/disable AI scoring
        """
        if response_threshold is not None:
            self.response_threshold = max(0.0, min(1.0, response_threshold))
            logger.info(f"Updated response threshold to {self.response_threshold}")

        if max_responses_per_minute is not None:
            self.max_responses_per_minute = max(1, max_responses_per_minute)
            logger.info(f"Updated rate limit to {self.max_responses_per_minute}/min")

        if enable_ai_scoring is not None:
            self.enable_ai_scoring = enable_ai_scoring
            logger.info(f"AI scoring {'enabled' if enable_ai_scoring else 'disabled'}")

    def get_statistics(self) -> Dict[str, any]:
        """
        Get filter statistics.

        Returns:
            Dictionary with current statistics
        """
        total_recent_responses = sum(
            len(responses) for responses in self._recent_responses.values()
        )

        return {
            'response_threshold': self.response_threshold,
            'max_responses_per_minute': self.max_responses_per_minute,
            'enable_ai_scoring': self.enable_ai_scoring,
            'recent_responses_total': total_recent_responses,
            'active_channels': len(self._recent_responses),
        }
