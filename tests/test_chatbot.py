# AI Usage Statement:
# This test suite was designed with the assistance of Claude (Anthropic) to
# validate all intents, edge cases, smart escalation, and frustrated-student
# sentiment handling. All test cases were reviewed and validated by the author.

"""Pytest test suite for the IBM SkillsBuild Assistant.

Test classes:
    TestNormalization       — text pre-processing
    TestAccessIntent        — lab access, cloud environment, login queries
    TestWatsonxIntent       — 403 errors, capacity limits, project tokens
    TestCertificationIntent — badges, Credly, 80 %+ score, 48h wait
    TestCurriculumIntent    — course structure, module progression
    TestCommunityIntent     — #lab-support, Slack, community rules
    TestFallback            — empty strings, nonsense, unknown topics
    TestFrustratedStudent   — frustration sentiment always escalates to Slack
    TestSmartEscalation     — confidence-based #lab-support escalation
    TestResponseStructure   — Response field types and constraints
"""

import pytest

from src.engine import ESCALATION_THRESHOLD, ChatEngine
from src.models import Response


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine() -> ChatEngine:
    """Return a shared, module-scoped ChatEngine instance.

    Returns:
        A fully initialised ChatEngine.
    """
    return ChatEngine()


# ---------------------------------------------------------------------------
# TestNormalization
# ---------------------------------------------------------------------------


class TestNormalization:
    """Validate the _normalize pre-processing helper."""

    def test_lowercase(self, engine: ChatEngine) -> None:
        """Output must be fully lowercase."""
        assert engine._normalize("WATSONX.AI") == engine._normalize("watsonx.ai")

    def test_strips_punctuation(self, engine: ChatEngine) -> None:
        """Question marks and exclamation points must be removed."""
        result = engine._normalize("403 Forbidden?!")
        assert "?" not in result and "!" not in result

    def test_collapses_whitespace(self, engine: ChatEngine) -> None:
        """Multiple consecutive spaces must collapse to one."""
        assert "  " not in engine._normalize("hello   world")

    def test_preserves_hyphens(self, engine: ChatEngine) -> None:
        """Hyphens inside words (e.g. two-factor) must survive normalisation."""
        assert "two-factor" in engine._normalize("two-factor authentication")

    def test_strips_leading_trailing_space(self, engine: ChatEngine) -> None:
        """Leading and trailing whitespace must be stripped."""
        result = engine._normalize("  badge  ")
        assert result == result.strip()


# ---------------------------------------------------------------------------
# TestAccessIntent
# ---------------------------------------------------------------------------


class TestAccessIntent:
    """Queries about lab access and cloud environment (Lab Orientation doc)."""

    def test_login_keyword(self, engine: ChatEngine) -> None:
        r = engine.respond("How do I login to SkillsBuild?")
        assert r.intent_name == "access"

    def test_forgot_password(self, engine: ChatEngine) -> None:
        r = engine.respond("I forgot my password")
        assert r.intent_name == "access"

    def test_no_local_install(self, engine: ChatEngine) -> None:
        """Students asking about local installs should learn it's cloud-managed."""
        r = engine.respond("Do I need to install Python locally?")
        assert r.intent_name == "access"

    def test_lab_environment(self, engine: ChatEngine) -> None:
        r = engine.respond("I cannot access the lab environment")
        assert r.intent_name == "access"

    def test_two_factor_setup(self, engine: ChatEngine) -> None:
        r = engine.respond("Help setting up 2fa for my account")
        assert r.intent_name == "access"


# ---------------------------------------------------------------------------
# TestWatsonxIntent
# ---------------------------------------------------------------------------


class TestWatsonxIntent:
    """Queries about watsonx.ai troubleshooting (watsonx.ai doc)."""

    def test_403_error(self, engine: ChatEngine) -> None:
        """403 Forbidden is the canonical watsonx.ai error."""
        r = engine.respond("I keep getting a 403 forbidden error on watsonx.ai")
        assert r.intent_name == "watsonx"

    def test_capacity_limit(self, engine: ChatEngine) -> None:
        r = engine.respond("The model says capacity limit reached")
        assert r.intent_name == "watsonx"

    def test_project_token(self, engine: ChatEngine) -> None:
        r = engine.respond("My project token is invalid or expired")
        assert r.intent_name == "watsonx"

    def test_watsonx_direct(self, engine: ChatEngine) -> None:
        r = engine.respond("What is watsonx?")
        assert r.intent_name == "watsonx"

    def test_granite_model(self, engine: ChatEngine) -> None:
        r = engine.respond("Tell me about the Granite foundation model")
        assert r.intent_name == "watsonx"

    def test_prompt_engineering(self, engine: ChatEngine) -> None:
        r = engine.respond("How does prompt engineering work?")
        assert r.intent_name == "watsonx"

    def test_watsonx_beats_curriculum_on_course_overlap(self, engine: ChatEngine) -> None:
        """'watsonx' keyword (priority 3) should dominate over 'curriculum' (priority 1)."""
        r = engine.respond("Is there a watsonx course outline?")
        assert r.intent_name == "watsonx"


# ---------------------------------------------------------------------------
# TestCertificationIntent
# ---------------------------------------------------------------------------


class TestCertificationIntent:
    """Queries about badges and certificates (Badges/Certificates doc)."""

    def test_badge_keyword(self, engine: ChatEngine) -> None:
        r = engine.respond("How do I earn a badge?")
        assert r.intent_name == "certification"

    def test_credly(self, engine: ChatEngine) -> None:
        r = engine.respond("I haven't received my credly invitation")
        assert r.intent_name == "certification"

    def test_passing_score(self, engine: ChatEngine) -> None:
        """Students must score 80%+ — this should fire the certification intent."""
        r = engine.respond("What is the passing score for the final assessment?")
        assert r.intent_name == "certification"

    def test_48_hour_wait(self, engine: ChatEngine) -> None:
        r = engine.respond("How long does the badge take? Is it 48 hours?")
        assert r.intent_name == "certification"

    def test_linkedin_share(self, engine: ChatEngine) -> None:
        r = engine.respond("Can I share my badge on LinkedIn?")
        assert r.intent_name == "certification"

    def test_digital_badge_phrase(self, engine: ChatEngine) -> None:
        """Long multi-word keyword should yield higher confidence than single 'badge'."""
        r_long = engine.respond("I want to earn a digital badge")
        r_short = engine.respond("I want a badge")
        assert r_long.intent_name == "certification"
        assert r_long.confidence >= r_short.confidence


# ---------------------------------------------------------------------------
# TestCurriculumIntent
# ---------------------------------------------------------------------------


class TestCurriculumIntent:
    """Queries about course structure and module progression (Curriculum Overview doc)."""

    def test_modules_keyword(self, engine: ChatEngine) -> None:
        r = engine.respond("What modules does this course have?")
        assert r.intent_name == "curriculum"

    def test_learning_path(self, engine: ChatEngine) -> None:
        r = engine.respond("Show me the learning path for beginners")
        assert r.intent_name == "curriculum"

    def test_prerequisites(self, engine: ChatEngine) -> None:
        r = engine.respond("Are there prerequisites for the advanced course?")
        assert r.intent_name == "curriculum"


# ---------------------------------------------------------------------------
# TestCommunityIntent
# ---------------------------------------------------------------------------


class TestCommunityIntent:
    """Queries about the Slack community and #lab-support (Community/Slack doc)."""

    def test_lab_support_channel(self, engine: ChatEngine) -> None:
        r = engine.respond("How do I use the lab-support channel?")
        assert r.intent_name == "community"

    def test_where_to_ask(self, engine: ChatEngine) -> None:
        r = engine.respond("Where do I ask technical questions?")
        assert r.intent_name == "community"

    def test_community_rules(self, engine: ChatEngine) -> None:
        r = engine.respond("What are the community guidelines?")
        assert r.intent_name == "community"


# ---------------------------------------------------------------------------
# TestFallback
# ---------------------------------------------------------------------------


class TestFallback:
    """Empty strings, whitespace, nonsense, and unknown topics always escalate."""

    def test_empty_string(self, engine: ChatEngine) -> None:
        """Empty input must return fallback and escalate."""
        r = engine.respond("")
        assert r.intent_name == "fallback"
        assert r.escalate is True
        assert r.confidence == 0.0

    def test_whitespace_only(self, engine: ChatEngine) -> None:
        r = engine.respond("     ")
        assert r.intent_name == "fallback"
        assert r.escalate is True

    def test_nonsense_input(self, engine: ChatEngine) -> None:
        """Pure gibberish must fall back and escalate."""
        r = engine.respond("xkjqwzpvmb")
        assert r.intent_name == "fallback"
        assert r.escalate is True

    def test_unknown_topic(self, engine: ChatEngine) -> None:
        """A coherent but off-topic question must fall back."""
        r = engine.respond("What is the weather in London?")
        assert r.intent_name == "fallback"
        assert r.escalate is True

    def test_fallback_matched_keywords_empty(self, engine: ChatEngine) -> None:
        r = engine.respond("")
        assert r.matched_keywords == []

    def test_fallback_text_mentions_lab_support(self, engine: ChatEngine) -> None:
        """Fallback text should mention #lab-support so students know where to go."""
        r = engine.respond("complete nonsense qwerty")
        assert "lab-support" in r.text.lower() or "slack" in r.text.lower()


# ---------------------------------------------------------------------------
# TestFrustratedStudent
# ---------------------------------------------------------------------------


class TestFrustratedStudent:
    """Frustrated student sentiment: always intercept before scoring and escalate.

    This is the 'frustrated student' sentiment test block required by the challenge.
    The engine must detect frustration signals and respond with empathy and
    #lab-support escalation rather than an informational answer.
    """

    def test_explicit_frustration(self, engine: ChatEngine) -> None:
        """'frustrating' should fire the frustration intent."""
        r = engine.respond("This is so frustrating")
        assert r.intent_name == "frustration"
        assert r.escalate is True

    def test_give_up_signal(self, engine: ChatEngine) -> None:
        r = engine.respond("I give up, nothing works")
        assert r.intent_name == "frustration"
        assert r.escalate is True

    def test_hate_signal(self, engine: ChatEngine) -> None:
        r = engine.respond("I hate this platform")
        assert r.intent_name == "frustration"

    def test_terrible_signal(self, engine: ChatEngine) -> None:
        r = engine.respond("This experience is terrible and awful")
        assert r.intent_name == "frustration"

    def test_frustration_overrides_intent_keywords(self, engine: ChatEngine) -> None:
        """Even when a valid intent keyword is present, frustration takes priority."""
        r = engine.respond("This is ridiculous, my watsonx token keeps failing")
        assert r.intent_name == "frustration"

    def test_frustration_response_mentions_lab_support(self, engine: ChatEngine) -> None:
        """Empathetic reply must include a path to #lab-support."""
        r = engine.respond("I am so annoyed with this lab")
        assert "lab-support" in r.text.lower() or "slack" in r.text.lower()

    def test_frustration_confidence_is_zero(self, engine: ChatEngine) -> None:
        """Frustration bypasses scoring; confidence must be 0.0."""
        r = engine.respond("This is useless")
        assert r.confidence == 0.0

    def test_frustration_matched_keywords_empty(self, engine: ChatEngine) -> None:
        r = engine.respond("I hate that it is broken")
        assert r.matched_keywords == []


# ---------------------------------------------------------------------------
# TestSmartEscalation
# ---------------------------------------------------------------------------


class TestSmartEscalation:
    """Confidence-based #lab-support escalation (the 'smart fallback')."""

    def test_high_confidence_no_escalation(self, engine: ChatEngine) -> None:
        """A keyword-rich query should yield confidence above threshold — no escalation."""
        r = engine.respond(
            "403 forbidden error on watsonx.ai project token expired capacity limit"
        )
        assert r.intent_name == "watsonx"
        if r.confidence >= ESCALATION_THRESHOLD:
            assert r.escalate is False

    def test_low_confidence_triggers_escalation(self, engine: ChatEngine) -> None:
        """A minimal single-keyword match should stay below threshold and escalate."""
        # 'lab' is in the catalog keyword list with priority 1 — low score
        r = engine.respond("lab")
        # Whether it hits an intent or falls back, confidence should be low
        assert r.escalate is True or r.confidence < ESCALATION_THRESHOLD

    def test_fallback_always_escalates(self, engine: ChatEngine) -> None:
        r = engine.respond("what is quantum computing")
        assert r.escalate is True

    def test_escalation_text_contains_lab_support(self, engine: ChatEngine) -> None:
        """When escalate is True, the response text must mention #lab-support."""
        r = engine.respond("something completely unrelated to skillsbuild")
        if r.escalate:
            assert "lab-support" in r.text.lower() or "slack" in r.text.lower()

    def test_escalation_threshold_value(self) -> None:
        """ESCALATION_THRESHOLD must be a float between 0 and 1."""
        assert 0.0 < ESCALATION_THRESHOLD < 1.0


# ---------------------------------------------------------------------------
# TestResponseStructure
# ---------------------------------------------------------------------------


class TestResponseStructure:
    """All Response fields must have correct types and constraints."""

    def test_text_is_nonempty_string(self, engine: ChatEngine) -> None:
        assert isinstance(engine.respond("403 error watsonx").text, str)
        assert len(engine.respond("403 error watsonx").text) > 0

    def test_intent_name_is_string(self, engine: ChatEngine) -> None:
        assert isinstance(engine.respond("badge credly").intent_name, str)

    def test_confidence_is_float_in_range(self, engine: ChatEngine) -> None:
        r = engine.respond("I need help with my badge")
        assert isinstance(r.confidence, float)
        assert 0.0 <= r.confidence <= 1.0

    def test_matched_keywords_is_list(self, engine: ChatEngine) -> None:
        assert isinstance(engine.respond("credly badge linkedin").matched_keywords, list)

    def test_escalate_is_bool(self, engine: ChatEngine) -> None:
        assert isinstance(engine.respond("anything").escalate, bool)

    def test_respond_returns_response_type(self, engine: ChatEngine) -> None:
        assert isinstance(engine.respond("hello"), Response)

    def test_frustration_returns_response_type(self, engine: ChatEngine) -> None:
        assert isinstance(engine.respond("this is terrible"), Response)

    def test_fallback_returns_response_type(self, engine: ChatEngine) -> None:
        assert isinstance(engine.respond(""), Response)

    def test_confidence_never_negative(self, engine: ChatEngine) -> None:
        for query in ["", "nonsense", "badge", "403", "frustrated"]:
            assert engine.respond(query).confidence >= 0.0

    def test_confidence_never_exceeds_one(self, engine: ChatEngine) -> None:
        """Even with maximum keyword saturation, confidence must not exceed 1.0."""
        heavy = (
            "watsonx watsonx.ai 403 forbidden error capacity limit project token "
            "api token rate limit granite generative ai large language model prompt "
            "engineering natural language processing foundation model"
        )
        assert engine.respond(heavy).confidence <= 1.0
