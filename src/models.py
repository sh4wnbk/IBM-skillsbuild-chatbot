# AI Usage Statement:
# This file was designed with the assistance of Claude (Anthropic) to establish
# data model conventions for the IBM SkillsBuild Assistant. All logic and
# docstrings were reviewed and validated by the author.

"""Data models for the IBM SkillsBuild Assistant chatbot.

Defines the three core dataclasses — Intent, MatchResult, and Response —
used throughout the engine pipeline.
"""

from dataclasses import dataclass, field


@dataclass
class Intent:
    """Represents a single conversational intent with keywords and responses.

    An intent groups a set of keywords that signal a particular student need,
    alongside a pool of responses drawn from official SkillsBuild documentation.

    Attributes:
        name: Unique identifier for the intent (e.g., ``"access"``, ``"watsonx"``).
        keywords: Keyword strings matched against normalised user input.
            Longer keywords contribute more to the weighted score.
        priority: Integer multiplier (1=low, 2=medium, 3=high) applied during
            scoring. Higher-priority intents score more strongly per keyword.
        responses: Pool of response strings, one chosen at random when this
            intent wins. Content sourced from official SkillsBuild documentation.
        examples: Example user phrases that should trigger this intent.
            Used for documentation and test design only.

    Example:
        >>> intent = Intent(
        ...     name="certification",
        ...     keywords=["badge", "credly"],
        ...     priority=2,
        ...     responses=["Badges are issued via Credly within 48 hours."],
        ...     examples=["How do I get my badge?"],
        ... )
        >>> intent.priority
        2
    """

    name: str
    keywords: list[str]
    priority: int
    responses: list[str]
    examples: list[str] = field(default_factory=list)


@dataclass
class MatchResult:
    """Scoring result for one intent against user input (internal use only).

    Produced during the ``_score_input`` phase of ``ChatEngine.respond()``.
    Not returned to callers; used to determine the winning intent.

    Attributes:
        intent: The Intent that was scored.
        score: Raw weighted score — sum of ``len(keyword) * intent.priority``
            for every keyword found in the normalised input.
        matched_keywords: Keywords from the intent that appeared in the input,
            in the order they were checked.

    Example:
        >>> from src.models import Intent, MatchResult
        >>> intent = Intent("access", ["password"], 2, ["Reset at login page."])
        >>> result = MatchResult(intent=intent, score=16.0, matched_keywords=["password"])
        >>> result.score
        16.0
    """

    intent: Intent
    score: float
    matched_keywords: list[str]


@dataclass
class Response:
    """The chatbot's reply envelope returned to callers.

    Wraps reply text with metadata so callers can inspect the engine's
    reasoning and apply threshold-based escalation logic.

    Attributes:
        text: The reply string to display to the student.
        intent_name: Name of the intent that fired. ``"fallback"`` when no
            intent matched; ``"frustration"`` when a frustration signal was
            detected.
        confidence: Float in ``[0.0, 1.0]``. 0.0 = no match (fallback),
            1.0 = theoretical maximum score achieved.
        matched_keywords: Keywords that contributed to the winning score.
            Empty list for fallback and frustration responses.
        escalate: When ``True``, the caller should display the #lab-support
            Slack escalation prompt alongside the response text.

    Example:
        >>> resp = Response(
        ...     text="Badges are issued via Credly within 48 hours.",
        ...     intent_name="certification",
        ...     confidence=0.82,
        ...     matched_keywords=["badge", "credly"],
        ...     escalate=False,
        ... )
        >>> resp.escalate
        False
    """

    text: str
    intent_name: str
    confidence: float
    matched_keywords: list[str]
    escalate: bool = False
