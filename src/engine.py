# AI Usage Statement:
# This file was designed with the assistance of Claude (Anthropic) to implement
# the weighted keyword-scoring algorithm and intent definitions sourced from
# official IBM SkillsBuild documentation. All logic and docstrings were
# reviewed and validated by the author.

"""Core chatbot engine for the IBM SkillsBuild Assistant.

Intent data sourced from:
- Curriculum Overview    : Course structure and module progression.
- Lab Orientation        : Managed cloud environments; no local setup needed.
- Community / Slack      : #lab-support for technical issues; search-first rules.
- Badges / Certificates  : Issued via Credly; 48-hour wait; 80 %+ final score.
- watsonx.ai             : 403 Forbidden errors, capacity limits, project tokens.

Weighted scoring formula:
    score += len(keyword) * intent.priority   (per matched keyword)
    confidence = raw_score / max_possible_score   (clamped to [0.0, 1.0])

Smart fallback:
    When confidence < ESCALATION_THRESHOLD, the ``Response.escalate`` flag is
    set to ``True`` and the caller is prompted to direct the student to
    #lab-support on the IBM SkillsBuild Slack workspace.
"""

import random
import re

from src.models import Intent, MatchResult, Response

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

#: Minimum confidence for a matched intent to be considered "reliable".
#: Below this, the response will include a #lab-support escalation prompt.
ESCALATION_THRESHOLD: float = 0.25

# ---------------------------------------------------------------------------
# Frustration signal words (checked before intent scoring)
# ---------------------------------------------------------------------------
_FRUSTRATION_SIGNALS: list[str] = [
    "frustrated",
    "frustrating",
    "annoyed",
    "angry",
    "hate",
    "stupid",
    "broken",
    "terrible",
    "awful",
    "useless",
    "doesnt work",
    "doesn't work",
    "not working",
    "nothing works",
    "give up",
    "i cant",
    "i can't",
    "impossible",
    "ridiculous",
    "this is bad",
]

# ---------------------------------------------------------------------------
# Static response strings
# ---------------------------------------------------------------------------

_FALLBACK_EMPTY = (
    "It looks like you sent an empty message. "
    "Try asking about lab access, watsonx.ai, badges, the course curriculum, "
    "or the SkillsBuild community."
)

_FALLBACK_UNKNOWN = (
    "I'm not sure about that topic yet. I specialise in IBM SkillsBuild topics: "
    "lab access & cloud environments, watsonx.ai troubleshooting, badges & "
    "certificates, course curriculum, and the Slack community.\n"
    "Could you rephrase, or pick one of those areas?"
)

_FALLBACK_NONSENSE = (
    "I didn't quite catch that. I can help with: lab access, watsonx.ai, "
    "digital badges, the course catalog, or the #lab-support Slack channel. "
    "What would you like to know?"
)

_FRUSTRATION_RESPONSE = (
    "I'm sorry you're having a tough time — that's completely understandable! "
    "Let me point you in the right direction.\n\n"
    "For hands-on technical issues, the fastest path to a human is the "
    "#lab-support channel on the IBM SkillsBuild Slack workspace. "
    "Please search existing threads before posting — someone may have already "
    "solved the same problem."
)

_ESCALATION_PROMPT = (
    "\n\n---\n"
    "Still stuck? Post in #lab-support on the IBM SkillsBuild Slack workspace. "
    "Search existing threads first — the answer is often already there."
)


class ChatEngine:
    """Keyword-based intent matching engine for the IBM SkillsBuild Assistant.

    Normalises user input, detects student frustration, scores all defined
    intents with a weighted keyword algorithm, and returns a structured
    ``Response``. Low-confidence matches automatically set ``Response.escalate``
    to prompt #lab-support Slack escalation.

    Attributes:
        intents: The list of ``Intent`` objects the engine matches against.

    Example:
        >>> engine = ChatEngine()
        >>> r = engine.respond("I'm getting a 403 error on watsonx.ai")
        >>> r.intent_name
        'watsonx'
        >>> 0.0 <= r.confidence <= 1.0
        True
    """

    def __init__(self) -> None:
        """Initialise the engine, build intents, and compute the max possible score."""
        self.intents: list[Intent] = self._build_intents()
        self._max_possible_score: float = self._compute_max_score()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def respond(self, user_input: str) -> Response:
        """Process raw user input and return the best-matching Response.

        Decision tree:
        1. Empty / whitespace-only  → fallback (empty sub-case, escalate=True).
        2. Normalise input.
        3. Frustration detected     → empathetic response with #lab-support link.
        4. Score all intents; pick the highest scorer.
        5. score == 0               → fallback (nonsense/unknown, escalate=True).
        6. confidence < threshold   → matched response + escalate=True.
        7. Otherwise                → matched response, escalate=False.

        Args:
            user_input: The raw string typed by the student.

        Returns:
            A ``Response`` with reply text, intent name, confidence, matched
            keywords, and an escalation flag.

        Example:
            >>> engine = ChatEngine()
            >>> r = engine.respond("how do I share my credly badge on linkedin?")
            >>> r.intent_name
            'certification'
        """
        if not user_input.strip():
            return Response(
                text=_FALLBACK_EMPTY,
                intent_name="fallback",
                confidence=0.0,
                matched_keywords=[],
                escalate=True,
            )

        normalized = self._normalize(user_input)

        if self._detect_frustration(normalized):
            return Response(
                text=_FRUSTRATION_RESPONSE,
                intent_name="frustration",
                confidence=0.0,
                matched_keywords=[],
                escalate=True,
            )

        results = self._score_input(normalized)
        if not results:
            return self._fallback_response(user_input)

        winning = max(results, key=lambda r: r.score)
        if winning.score == 0:
            return self._fallback_response(user_input)

        raw_confidence = winning.score / self._max_possible_score
        confidence = min(raw_confidence, 1.0)
        escalate = confidence < ESCALATION_THRESHOLD

        text = self._select_response(winning.intent)
        if escalate:
            text += _ESCALATION_PROMPT

        return Response(
            text=text,
            intent_name=winning.intent.name,
            confidence=confidence,
            matched_keywords=winning.matched_keywords,
            escalate=escalate,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _normalize(self, text: str) -> str:
        """Lowercase, strip punctuation (keep hyphens/apostrophes), collapse spaces.

        Args:
            text: Raw input string.

        Returns:
            Normalised string ready for keyword matching.

        Example:
            >>> engine = ChatEngine()
            >>> engine._normalize("403 Forbidden Error!!")
            '403 forbidden error'
        """
        text = text.lower().strip()
        text = re.sub(r"[^\w\s\-']", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _detect_frustration(self, normalized: str) -> bool:
        """Return True if the normalised text contains any frustration signal.

        Args:
            normalized: Normalised user input from ``_normalize``.

        Returns:
            ``True`` if at least one frustration signal substring is present.

        Example:
            >>> engine = ChatEngine()
            >>> engine._detect_frustration("this is so frustrating")
            True
        """
        return any(signal in normalized for signal in _FRUSTRATION_SIGNALS)

    def _score_input(self, normalized: str) -> list[MatchResult]:
        """Score every intent against normalised input and return non-zero results.

        For each intent keyword found as a substring of ``normalized``:
            contribution = len(keyword) * intent.priority

        Args:
            normalized: Normalised user input from ``_normalize``.

        Returns:
            List of ``MatchResult`` objects for intents with score > 0,
            sorted by score descending.
        """
        results: list[MatchResult] = []
        for intent in self.intents:
            score = 0.0
            matched: list[str] = []
            for keyword in intent.keywords:
                if keyword in normalized:
                    score += len(keyword) * intent.priority
                    matched.append(keyword)
            if score > 0:
                results.append(MatchResult(intent=intent, score=score, matched_keywords=matched))
        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def _select_response(self, intent: Intent) -> str:
        """Randomly select one response from the intent's response pool.

        Args:
            intent: The winning Intent.

        Returns:
            A randomly chosen response string.
        """
        return random.choice(intent.responses)

    def _fallback_response(self, original_input: str) -> Response:
        """Return an escalation-flagged fallback Response for unmatched input.

        Distinguishes gibberish (< 3 alpha chars) from coherent-but-unknown
        queries to provide a more helpful message in each case.

        Args:
            original_input: The original un-normalised user input.

        Returns:
            A ``Response`` with ``intent_name="fallback"`` and ``escalate=True``.
        """
        normalized = self._normalize(original_input)
        alpha_only = re.sub(r"[^a-z]", "", normalized)
        text = _FALLBACK_NONSENSE if len(alpha_only) < 3 else _FALLBACK_UNKNOWN
        text += _ESCALATION_PROMPT
        return Response(
            text=text,
            intent_name="fallback",
            confidence=0.0,
            matched_keywords=[],
            escalate=True,
        )

    def _compute_max_score(self) -> float:
        """Compute the theoretical maximum score across all defined intents.

        Used to normalise raw scores into a ``[0, 1]`` confidence range.

        Returns:
            Maximum possible ``sum(len(kw) * priority for kw in keywords)``
            across all intents. Returns 1.0 if no intents are defined.
        """
        if not self.intents:
            return 1.0
        return max(
            sum(len(kw) * intent.priority for kw in intent.keywords)
            for intent in self.intents
        )

    def _build_intents(self) -> list[Intent]:
        """Construct the full list of intents from SkillsBuild documentation data.

        Intent data sourced from the five official documentation links:
        Curriculum Overview, Lab Orientation, Community/Slack,
        Badges/Certificates, and watsonx.ai troubleshooting.

        Returns:
            List of five ``Intent`` objects.
        """
        return [
            # ------------------------------------------------------------------
            # Intent 1: access  (priority 2)
            # Source: Lab Orientation — managed cloud; no local setup.
            # ------------------------------------------------------------------
            Intent(
                name="access",
                priority=2,
                keywords=[
                    "login",
                    "log in",
                    "sign in",
                    "password",
                    "reset password",
                    "forgot password",
                    "account",
                    "locked out",
                    "locked account",
                    "two-factor",
                    "2fa",
                    "authentication",
                    "username",
                    "email verification",
                    "activate account",
                    "registration",
                    "cloud environment",
                    "managed environment",
                    "no install",
                    "no local install",
                    "install",
                    "python install",
                    "lab environment",
                    "lab access",
                    "unable to access",
                    "cannot access",
                ],
                responses=[
                    (
                        "IBM SkillsBuild labs run in a fully managed cloud environment — "
                        "no local Python installation or software setup is required on your "
                        "machine. Everything runs in the browser.\n\n"
                        "If you cannot access the lab, first try logging out and back in. "
                        "For persistent login issues, visit the login page and use "
                        "'Forgot Password' to reset your credentials. Activation emails "
                        "expire after 24 hours — check your spam folder."
                    ),
                    (
                        "Your SkillsBuild lab environment is cloud-hosted, so you do not need "
                        "to install Python, Jupyter, or any other software locally.\n\n"
                        "For account or access problems: clear your browser cache, disable "
                        "VPN if active, and ensure cookies are enabled. If 2FA is failing, "
                        "re-sync your authenticator app clock."
                    ),
                ],
                examples=[
                    "I can't access the lab",
                    "Do I need to install Python?",
                    "My account is locked",
                    "I forgot my password",
                ],
            ),

            # ------------------------------------------------------------------
            # Intent 2: watsonx  (priority 3 — highest)
            # Source: watsonx.ai — 403 errors, capacity limits, project tokens.
            # ------------------------------------------------------------------
            Intent(
                name="watsonx",
                priority=3,
                keywords=[
                    "watsonx",
                    "watsonx.ai",
                    "403",
                    "403 forbidden",
                    "forbidden error",
                    "capacity",
                    "capacity limit",
                    "server capacity",
                    "project token",
                    "api token",
                    "token expired",
                    "token invalid",
                    "rate limit",
                    "quota",
                    "inference error",
                    "model inference",
                    "prompt lab",
                    "foundation model",
                    "granite",
                    "generative ai",
                    "gen ai",
                    "large language model",
                    "llm",
                    "prompt engineering",
                    "natural language processing",
                    "nlp",
                    "watson",
                ],
                responses=[
                    (
                        "Common watsonx.ai issues and fixes:\n\n"
                        "• 403 Forbidden error: Your project API token has expired or lacks "
                        "the correct IAM role. Regenerate your token in the IBM Cloud IAM "
                        "console and update the project settings in watsonx.ai.\n\n"
                        "• Capacity limit reached: IBM Watson servers are at peak load. "
                        "Wait a few minutes and retry. Avoid submitting large batch jobs "
                        "during busy periods (typically weekday mornings UTC).\n\n"
                        "• Project token issues: Ensure your token is scoped to the correct "
                        "project ID. A mismatch between token and project causes silent "
                        "auth failures."
                    ),
                    (
                        "If you see a 403 Forbidden on watsonx.ai, follow these steps:\n"
                        "1. Open IBM Cloud → Manage → Access (IAM) → API keys.\n"
                        "2. Create a new API key or regenerate the existing one.\n"
                        "3. In watsonx.ai, go to Project → Manage → Access Control and "
                        "update the token.\n\n"
                        "If the error persists after a token refresh, the project may have "
                        "hit its capacity quota. Check the IBM Cloud usage dashboard or wait "
                        "and retry after 5–10 minutes."
                    ),
                    (
                        "watsonx.ai Prompt Lab tips:\n\n"
                        "• If a foundation model (e.g. Granite) returns a timeout, reduce "
                        "your max token count and retry.\n"
                        "• Capacity errors are temporary — IBM automatically scales, but "
                        "peak demand can cause delays of 2–5 minutes.\n"
                        "• Always validate your project token scope before starting a lab "
                        "session to avoid mid-lab interruptions."
                    ),
                ],
                examples=[
                    "I'm getting a 403 error on watsonx.ai",
                    "The model says capacity limit reached",
                    "My project token is not working",
                    "What is the Granite foundation model?",
                ],
            ),

            # ------------------------------------------------------------------
            # Intent 3: certification  (priority 2)
            # Source: Badges/Certificates — Credly; 48h wait; 80%+ score.
            # ------------------------------------------------------------------
            Intent(
                name="certification",
                priority=2,
                keywords=[
                    "badge",
                    "digital badge",
                    "certificate",
                    "certification",
                    "credential",
                    "credly",
                    "acclaim",
                    "earn badge",
                    "80 percent",
                    "80%",
                    "passing score",
                    "passing grade",
                    "final score",
                    "final assessment",
                    "assessment score",
                    "48 hours",
                    "48h",
                    "badge delay",
                    "completed course",
                    "course completion",
                    "linkedin",
                    "share badge",
                    "verify certificate",
                    "proof of completion",
                    "transcript",
                    "exam",
                    "quiz",
                ],
                responses=[
                    (
                        "IBM SkillsBuild badges and certificates:\n\n"
                        "• Badges are issued through Credly within 48 hours of course "
                        "completion — check your email (including spam) for an invitation.\n\n"
                        "• You must achieve 80% or higher on the final assessment to earn "
                        "a badge. The score threshold is fixed and cannot be waived.\n\n"
                        "• Once claimed on Credly, you can share your badge directly to "
                        "LinkedIn with a single click. Each badge has a unique, verifiable URL."
                    ),
                    (
                        "Haven't received your badge after completing a course?\n\n"
                        "1. Confirm you scored 80%+ on the final assessment.\n"
                        "2. Check your email spam folder for a Credly invitation.\n"
                        "3. If it has been more than 48 hours and no email arrived, "
                        "contact SkillsBuild support with a screenshot of your completion page."
                    ),
                    (
                        "To verify a SkillsBuild certificate or badge:\n"
                        "• Visit https://credly.com and search for the recipient's name.\n"
                        "• Each badge URL is cryptographically unique and can be shared as "
                        "proof of completion with employers or on LinkedIn.\n\n"
                        "Note: The 48-hour issuance window begins from when your final "
                        "assessment score is processed, not from when you click 'Submit'."
                    ),
                ],
                examples=[
                    "How do I get my badge?",
                    "I scored over 80% but no badge arrived",
                    "How long does Credly take?",
                    "Can I add my certificate to LinkedIn?",
                ],
            ),

            # ------------------------------------------------------------------
            # Intent 4: curriculum  (priority 1)
            # Source: Curriculum Overview — course structure, module progression.
            # ------------------------------------------------------------------
            Intent(
                name="curriculum",
                priority=1,
                keywords=[
                    "curriculum",
                    "course structure",
                    "module",
                    "modules",
                    "progression",
                    "learning path",
                    "course outline",
                    "syllabus",
                    "what topics",
                    "course content",
                    "course overview",
                    "lesson",
                    "lessons",
                    "unit",
                    "units",
                    "what do i learn",
                    "what will i learn",
                    "prerequisites",
                    "beginner",
                    "advanced",
                    "intermediate",
                ],
                responses=[
                    (
                        "IBM SkillsBuild courses are structured in sequential modules. "
                        "Each module builds on the previous one, so it is recommended to "
                        "follow the progression order rather than jumping ahead.\n\n"
                        "Courses typically include:\n"
                        "• Concept lessons (videos + readings)\n"
                        "• Hands-on labs in the managed cloud environment\n"
                        "• Knowledge checks and a graded final assessment (80%+ to pass)\n\n"
                        "Check the course overview page for a full module list and any "
                        "stated prerequisites before enrolling."
                    ),
                    (
                        "The SkillsBuild curriculum is organised into progressive learning "
                        "paths. Beginner paths require no prior experience; intermediate and "
                        "advanced paths list prerequisites on their overview pages.\n\n"
                        "To see a course outline before enrolling, click the course title "
                        "and scroll to the 'What you'll learn' section."
                    ),
                ],
                examples=[
                    "What modules are in this course?",
                    "Is there a prerequisite for the AI course?",
                    "Show me the course structure",
                    "What do I learn in the beginner path?",
                ],
            ),

            # ------------------------------------------------------------------
            # Intent 5: community  (priority 2)
            # Source: Community/Slack — #lab-support; search-first rules.
            # ------------------------------------------------------------------
            Intent(
                name="community",
                priority=2,
                keywords=[
                    "slack",
                    "lab-support",
                    "#lab-support",
                    "community",
                    "help channel",
                    "support channel",
                    "post question",
                    "ask question",
                    "search first",
                    "community rules",
                    "community guidelines",
                    "where to ask",
                    "where do i ask",
                    "who to contact",
                    "technical support",
                    "human support",
                    "live support",
                    "contact support",
                ],
                responses=[
                    (
                        "For technical issues during SkillsBuild labs:\n\n"
                        "1. Join the IBM SkillsBuild Slack workspace (link on your course page).\n"
                        "2. Search the #lab-support channel for your issue — most common "
                        "problems have already been answered.\n"
                        "3. If no existing thread resolves your issue, post a new message "
                        "with: your course name, the specific error message, and what you "
                        "already tried.\n\n"
                        "Community rule: Search before posting. Duplicate questions slow "
                        "response times for everyone."
                    ),
                    (
                        "The IBM SkillsBuild community uses Slack for peer and instructor "
                        "support. The primary channel for lab issues is #lab-support.\n\n"
                        "When posting, include:\n"
                        "• Course and module name\n"
                        "• Exact error message or screenshot\n"
                        "• Steps you have already tried\n\n"
                        "This helps the community (and instructors) respond quickly and "
                        "accurately."
                    ),
                ],
                examples=[
                    "Where do I ask for help?",
                    "How do I use the Slack channel?",
                    "Who can I contact for technical support?",
                    "What are the community rules?",
                ],
            ),
        ]
