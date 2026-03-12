# AI Usage Statement:
# This test suite was designed with the assistance of Claude (Anthropic) to
# cover all intents, edge cases, and scoring invariants. All test cases were
# reviewed and validated by the author.

"""Pytest test suite for the IBM SkillsBuild Assistant ChatEngine.

Tests are organised into classes by concern:
- TestNormalization    — text pre-processing
- TestAccessIntent    — login / account / 2FA queries
- TestWatsonxIntent   — IBM watsonx AI platform queries
- TestCertification   — badge, Credly, certificate queries
- TestCatalogIntent   — course catalog and learning path queries
- TestFallback        — empty input, nonsense, unknown topics
- TestFrustration     — frustration signals intercept before scoring
- TestWeightedScoring — scoring algorithm invariants
- TestResponseStructure — Response field types and constraints
"""

import pytest

from src.engine import ChatEngine
from src.models import Response


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine() -> ChatEngine:
    """Return a single ChatEngine instance shared across the module.

    Returns:
        A fully initialised ChatEngine.
    """
    return ChatEngine()


# ---------------------------------------------------------------------------
# TestNormalization
# ---------------------------------------------------------------------------


class TestNormalization:
    """Tests for the _normalize helper method."""

    def test_lowercase(self, engine: ChatEngine) -> None:
        """Normalised text should be all lowercase."""
        result = engine._normalize("HELLO WORLD")
        assert result == result.lower()

    def test_strips_punctuation(self, engine: ChatEngine) -> None:
        """Question marks and exclamation points should be removed."""
        result = engine._normalize("What is watsonx?!")
        assert "?" not in result
        assert "!" not in result

    def test_collapses_whitespace(self, engine: ChatEngine) -> None:
        """Multiple consecutive spaces should collapse to a single space."""
        result = engine._normalize("hello   world")
        assert "  " not in result

    def test_preserves_hyphens(self, engine: ChatEngine) -> None:
        """Hyphens inside words should be preserved (e.g. two-factor)."""
        result = engine._normalize("two-factor authentication")
        assert "two-factor" in result

    def test_strips_leading_trailing_whitespace(self, engine: ChatEngine) -> None:
        """Leading and trailing whitespace should be stripped."""
        result = engine._normalize("  hello  ")
        assert result == result.strip()


# ---------------------------------------------------------------------------
# TestAccessIntent
# ---------------------------------------------------------------------------


class TestAccessIntent:
    """Tests for the 'access' intent (login, password, 2FA, account)."""

    def test_login_keyword(self, engine: ChatEngine) -> None:
        """'login' should fire the access intent."""
        r = engine.respond("How do I login to my account?")
        assert r.intent_name == "access"

    def test_password_reset(self, engine: ChatEngine) -> None:
        """'forgot my password' should fire the access intent."""
        r = engine.respond("I forgot my password")
        assert r.intent_name == "access"

    def test_two_factor(self, engine: ChatEngine) -> None:
        """'2fa' should fire the access intent."""
        r = engine.respond("I need help setting up 2fa")
        assert r.intent_name == "access"

    def test_locked_out(self, engine: ChatEngine) -> None:
        """'locked out' should fire the access intent."""
        r = engine.respond("I'm locked out of my account")
        assert r.intent_name == "access"

    def test_reset_password_phrase(self, engine: ChatEngine) -> None:
        """'reset password' (multi-word keyword) should fire access."""
        r = engine.respond("How do I reset password?")
        assert r.intent_name == "access"


# ---------------------------------------------------------------------------
# TestWatsonxIntent
# ---------------------------------------------------------------------------


class TestWatsonxIntent:
    """Tests for the 'watsonx' intent (IBM AI platform, Gen AI, Granite)."""

    def test_watsonx_direct(self, engine: ChatEngine) -> None:
        """'watsonx' should fire the watsonx intent."""
        r = engine.respond("What is watsonx?")
        assert r.intent_name == "watsonx"

    def test_generative_ai(self, engine: ChatEngine) -> None:
        """'generative ai' should fire the watsonx intent."""
        r = engine.respond("I want to learn about generative ai")
        assert r.intent_name == "watsonx"

    def test_granite_model(self, engine: ChatEngine) -> None:
        """'granite' should fire the watsonx intent."""
        r = engine.respond("Tell me about the Granite model")
        assert r.intent_name == "watsonx"

    def test_prompt_engineering(self, engine: ChatEngine) -> None:
        """'prompt engineering' should fire the watsonx intent."""
        r = engine.respond("Is there a course on prompt engineering?")
        assert r.intent_name == "watsonx"

    def test_watsonx_beats_catalog_on_overlap(self, engine: ChatEngine) -> None:
        """'watsonx course' — watsonx (priority 3) should beat catalog (priority 1)."""
        r = engine.respond("Is there a watsonx course?")
        assert r.intent_name == "watsonx"

    def test_llm_keyword(self, engine: ChatEngine) -> None:
        """'llm' should fire the watsonx intent."""
        r = engine.respond("What LLM does IBM use?")
        assert r.intent_name == "watsonx"


# ---------------------------------------------------------------------------
# TestCertificationIntent
# ---------------------------------------------------------------------------


class TestCertificationIntent:
    """Tests for the 'certification' intent (badges, Credly, certificates)."""

    def test_badge_keyword(self, engine: ChatEngine) -> None:
        """'badge' should fire the certification intent."""
        r = engine.respond("How do I get a badge?")
        assert r.intent_name == "certification"

    def test_credly(self, engine: ChatEngine) -> None:
        """'credly' should fire the certification intent."""
        r = engine.respond("I haven't received my credly badge")
        assert r.intent_name == "certification"

    def test_linkedin_share(self, engine: ChatEngine) -> None:
        """'linkedin' should fire the certification intent."""
        r = engine.respond("Can I share my badge on linkedin?")
        assert r.intent_name == "certification"

    def test_certificate_verify(self, engine: ChatEngine) -> None:
        """'certificate' should fire the certification intent."""
        r = engine.respond("How do I verify my certificate?")
        assert r.intent_name == "certification"

    def test_digital_badge_phrase(self, engine: ChatEngine) -> None:
        """'digital badge' (long keyword) should fire certification with high confidence."""
        r = engine.respond("I want to earn a digital badge")
        assert r.intent_name == "certification"
        assert r.confidence > 0.0


# ---------------------------------------------------------------------------
# TestCatalogIntent
# ---------------------------------------------------------------------------


class TestCatalogIntent:
    """Tests for the 'catalog' intent (courses, learning paths)."""

    def test_courses_keyword(self, engine: ChatEngine) -> None:
        """'courses' should fire the catalog intent (no competing high-priority keywords)."""
        r = engine.respond("What free courses are available?")
        assert r.intent_name in ("catalog", "watsonx")  # watsonx has 'ai course' keyword
        # For a plain "courses" query without watsonx-specific words, catalog should win
        r2 = engine.respond("What courses do you have?")
        # catalog has 'courses' (7 * 1 = 7); watsonx has no match → catalog wins
        assert r2.intent_name == "catalog"

    def test_learning_path(self, engine: ChatEngine) -> None:
        """'learning path' should fire the catalog intent."""
        r = engine.respond("Show me learning paths for data science")
        assert r.intent_name == "catalog"

    def test_tutorial_keyword(self, engine: ChatEngine) -> None:
        """'tutorial' should fire the catalog intent."""
        r = engine.respond("Is there a tutorial for beginners?")
        assert r.intent_name == "catalog"


# ---------------------------------------------------------------------------
# TestFallback
# ---------------------------------------------------------------------------


class TestFallback:
    """Tests for fallback responses when no intent matches."""

    def test_empty_string(self, engine: ChatEngine) -> None:
        """Empty string should return a fallback response."""
        r = engine.respond("")
        assert r.intent_name == "fallback"
        assert r.confidence == 0.0

    def test_whitespace_only(self, engine: ChatEngine) -> None:
        """Whitespace-only input should return a fallback response."""
        r = engine.respond("   ")
        assert r.intent_name == "fallback"
        assert r.confidence == 0.0

    def test_nonsense_input(self, engine: ChatEngine) -> None:
        """Pure nonsense (no matching keywords) should return fallback."""
        r = engine.respond("asdfghjkl qwerty")
        assert r.intent_name == "fallback"

    def test_unknown_topic(self, engine: ChatEngine) -> None:
        """An unrelated but coherent question should return fallback."""
        r = engine.respond("What is the weather in London today?")
        assert r.intent_name == "fallback"

    def test_fallback_confidence_is_zero(self, engine: ChatEngine) -> None:
        """Fallback responses should always have confidence 0.0."""
        r = engine.respond("xyz123 no match here at all")
        assert r.confidence == 0.0

    def test_fallback_matched_keywords_empty(self, engine: ChatEngine) -> None:
        """Fallback responses should have an empty matched_keywords list."""
        r = engine.respond("")
        assert r.matched_keywords == []


# ---------------------------------------------------------------------------
# TestFrustration
# ---------------------------------------------------------------------------


class TestFrustration:
    """Tests for frustration signal detection (pre-scoring intercept)."""

    def test_explicit_frustration(self, engine: ChatEngine) -> None:
        """'frustrating' alone should trigger the frustration response."""
        r = engine.respond("This is so frustrating")
        assert r.intent_name == "frustration"

    def test_give_up(self, engine: ChatEngine) -> None:
        """'give up' should trigger the frustration response."""
        r = engine.respond("I give up nothing works")
        assert r.intent_name == "frustration"

    def test_frustration_overrides_intent(self, engine: ChatEngine) -> None:
        """Frustration signal mixed with an intent keyword should still fire frustration."""
        r = engine.respond("I'm so frustrated about my login issue")
        assert r.intent_name == "frustration"

    def test_frustration_confidence_is_zero(self, engine: ChatEngine) -> None:
        """Frustration responses should have confidence 0.0 (no scoring was done)."""
        r = engine.respond("this is ridiculous and awful")
        assert r.confidence == 0.0

    def test_frustration_matched_keywords_empty(self, engine: ChatEngine) -> None:
        """Frustration responses should have an empty matched_keywords list."""
        r = engine.respond("I hate this broken system")
        assert r.matched_keywords == []


# ---------------------------------------------------------------------------
# TestWeightedScoring
# ---------------------------------------------------------------------------


class TestWeightedScoring:
    """Tests for invariants of the weighted keyword scoring algorithm."""

    def test_longer_keyword_scores_higher(self, engine: ChatEngine) -> None:
        """'digital badge' (12 chars) should score higher than 'badge' (5 chars) alone."""
        results_long = engine._score_input("i want to earn a digital badge")
        results_short = engine._score_input("i want to earn a badge")
        # Both should fire the certification intent
        cert_long = next((r for r in results_long if r.intent.name == "certification"), None)
        cert_short = next((r for r in results_short if r.intent.name == "certification"), None)
        assert cert_long is not None and cert_short is not None
        assert cert_long.score > cert_short.score

    def test_higher_priority_wins_overlap(self, engine: ChatEngine) -> None:
        """On ambiguous input, the higher-priority intent should win."""
        # 'watsonx' (priority 3) vs 'catalog' (priority 1) on overlapping 'course'
        r = engine.respond("watsonx course overview")
        assert r.intent_name == "watsonx"

    def test_confidence_is_clamped_to_one(self, engine: ChatEngine) -> None:
        """Confidence should never exceed 1.0."""
        # Throw the most keyword-rich query possible at the engine
        r = engine.respond(
            "watsonx watsonx.ai watsonx.data generative ai granite llm prompt "
            "foundation model machine learning natural language processing"
        )
        assert r.confidence <= 1.0

    def test_confidence_is_nonnegative(self, engine: ChatEngine) -> None:
        """Confidence should never be negative."""
        r = engine.respond("I forgot my password")
        assert r.confidence >= 0.0

    def test_matched_keywords_contributed_to_score(self, engine: ChatEngine) -> None:
        """Every keyword in matched_keywords should actually appear in the input."""
        query = "I need help with my password reset"
        r = engine.respond(query)
        normalized = engine._normalize(query)
        for kw in r.matched_keywords:
            assert kw in normalized, f"Keyword '{kw}' not found in normalised input."

    def test_max_possible_score_positive(self, engine: ChatEngine) -> None:
        """The computed max possible score should be a positive float."""
        assert engine._max_possible_score > 0.0


# ---------------------------------------------------------------------------
# TestResponseStructure
# ---------------------------------------------------------------------------


class TestResponseStructure:
    """Tests that every Response returned has the correct field types."""

    def test_response_text_is_nonempty_string(self, engine: ChatEngine) -> None:
        """response.text should be a non-empty string."""
        r = engine.respond("What is watsonx?")
        assert isinstance(r.text, str)
        assert len(r.text) > 0

    def test_response_intent_name_is_string(self, engine: ChatEngine) -> None:
        """response.intent_name should be a string."""
        r = engine.respond("I forgot my password")
        assert isinstance(r.intent_name, str)

    def test_response_confidence_is_float(self, engine: ChatEngine) -> None:
        """response.confidence should be a float (or int coercible to float)."""
        r = engine.respond("How do I get a badge?")
        assert isinstance(r.confidence, float)

    def test_response_matched_keywords_is_list(self, engine: ChatEngine) -> None:
        """response.matched_keywords should be a list."""
        r = engine.respond("Tell me about Credly badges")
        assert isinstance(r.matched_keywords, list)

    def test_response_is_response_type(self, engine: ChatEngine) -> None:
        """respond() should always return a Response instance."""
        r = engine.respond("anything at all")
        assert isinstance(r, Response)

    def test_fallback_returns_response_type(self, engine: ChatEngine) -> None:
        """Fallback path should still return a Response instance."""
        r = engine.respond("")
        assert isinstance(r, Response)

    def test_frustration_returns_response_type(self, engine: ChatEngine) -> None:
        """Frustration path should still return a Response instance."""
        r = engine.respond("I'm so frustrated with this")
        assert isinstance(r, Response)
