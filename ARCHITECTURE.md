# Architecture — IBM SkillsBuild Assistant

## AI Usage Statement

The UML diagram and architectural descriptions were produced with assistance
from Claude (Anthropic). All design decisions were reviewed and validated by
the author.

---

## Text-Based UML Class Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                           src/models.py                              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────────────────────┐                                   │
│  │           Intent              │  @dataclass                       │
│  ├───────────────────────────────┤                                   │
│  │ + name        : str           │                                   │
│  │ + keywords    : list[str]     │                                   │
│  │ + priority    : int           │  1=low  2=medium  3=high          │
│  │ + responses   : list[str]     │  sourced from SkillsBuild docs    │
│  │ + examples    : list[str]     │  for testing / documentation      │
│  └───────────────┬───────────────┘                                   │
│                  │ referenced by                                      │
│  ┌───────────────▼───────────────┐                                   │
│  │         MatchResult           │  @dataclass  (engine-internal)    │
│  ├───────────────────────────────┤                                   │
│  │ + intent           : Intent   │                                   │
│  │ + score            : float    │  sum(len(kw)*priority)            │
│  │ + matched_keywords : list[str]│                                   │
│  └───────────────────────────────┘                                   │
│                                                                      │
│  ┌───────────────────────────────┐                                   │
│  │           Response            │  @dataclass  (public output)      │
│  ├───────────────────────────────┤                                   │
│  │ + text             : str      │                                   │
│  │ + intent_name      : str      │  "fallback" / "frustration" / ... │
│  │ + confidence       : float    │  [0.0, 1.0]                       │
│  │ + matched_keywords : list[str]│                                   │
│  │ + escalate         : bool     │  True → show #lab-support prompt  │
│  └───────────────────────────────┘                                   │
│                                                                      │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│                           src/engine.py                              │
├──────────────────────────────────────────────────────────────────────┤
│  ESCALATION_THRESHOLD : float = 0.25                                 │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │                        ChatEngine                              │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │ - intents             : list[Intent]                           │  │
│  │ - _max_possible_score : float                                  │  │
│  ├────────────────────────────────────────────────────────────────┤  │
│  │ + respond(user_input: str) -> Response              [public]   │  │
│  │ - _normalize(text: str) -> str                                 │  │
│  │ - _detect_frustration(text: str) -> bool                       │  │
│  │ - _score_input(text: str) -> list[MatchResult]                 │  │
│  │ - _select_response(intent: Intent) -> str                      │  │
│  │ - _fallback_response(input: str) -> Response                   │  │
│  │ - _build_intents() -> list[Intent]                             │  │
│  │ - _compute_max_score() -> float                                │  │
│  └────────────────────────┬───────────────────────────────────────┘  │
│                            │ owns 5 × Intent                          │
│                            │ (access, watsonx, certification,         │
│                            │  curriculum, community)                  │
│                            │ returns Response                         │
└────────────────────────────┼─────────────────────────────────────────┘
                             │ instantiates
┌────────────────────────────▼─────────────────────────────────────────┐
│                            main.py                                   │
├──────────────────────────────────────────────────────────────────────┤
│  main() -> None                                                      │
│    ├── Instantiates ChatEngine                                       │
│    ├── Prints welcome banner                                         │
│    └── REPL loop:                                                    │
│          input("You: ")                                              │
│              └──► engine.respond(user_input)                         │
│                       └──► print response.text                       │
│                       └──► if response.escalate: show Slack prompt   │
│                       └──► print [intent, confidence, escalate]      │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Intent Summary (sourced from SkillsBuild docs)

| Intent          | Priority | Source Document        | Key Topics                                   |
|-----------------|----------|------------------------|----------------------------------------------|
| `access`        | 2        | Lab Orientation        | Cloud environment, login, no local install   |
| `watsonx`       | 3        | watsonx.ai             | 403 errors, capacity limits, project tokens  |
| `certification` | 2        | Badges / Certificates  | Credly, 48h wait, 80%+ score, LinkedIn       |
| `curriculum`    | 1        | Curriculum Overview    | Module progression, learning paths           |
| `community`     | 2        | Community / Slack      | #lab-support, search-first, post guidelines  |

---

## Data Flow Diagram

```
  stdin  (student types a message)
      │
      ▼
  main.py ── input("You: ") ──► user_input: str
      │
      └──► ChatEngine.respond(user_input)
               │
               ├─ EMPTY CHECK ──────────────────────────────► fallback Response
               │  user_input.strip() == ""                    escalate=True
               │
               ├─ _normalize(user_input)
               │   • lowercase
               │   • strip punctuation (preserve hyphens/apostrophes)
               │   • collapse whitespace
               │            │
               │            ▼  normalized: str
               │
               ├─ _detect_frustration(normalized) ──────────► frustration Response
               │   checks substring signals                    escalate=True
               │   ("frustrated", "give up", "useless", …)
               │
               ├─ _score_input(normalized)
               │   for each Intent (5 total):
               │     for each keyword in intent.keywords:
               │       if keyword in normalized:
               │         score += len(keyword) * intent.priority
               │   → list[MatchResult], sorted desc by score
               │
               ├─ max(MatchResult by score)
               │   score == 0 ─────────────────────────────► fallback Response
               │                                              escalate=True
               │
               ├─ confidence = min(score / max_possible, 1.0)
               │
               ├─ escalate = (confidence < ESCALATION_THRESHOLD)
               │
               ├─ _select_response(winning_intent)
               │   random.choice(intent.responses)
               │   + _ESCALATION_PROMPT appended if escalate=True
               │
               └──► Response(text, intent_name, confidence,
                             matched_keywords, escalate)
      │
      ▼
  main.py
      ├── print(response.text)
      ├── (escalate flag already embedded in text when True)
      └── print [intent=X, confidence=Y.YY, escalate=Z]
      │
      ▼
  stdout  (displayed to student)
```

---

## Module Dependency Graph

```
  main.py
    └── src.engine   (ChatEngine, ESCALATION_THRESHOLD)
          ├── src.models  (Intent, MatchResult, Response)
          └── stdlib: random, re

  tests/test_chatbot.py
    ├── src.engine   (ChatEngine, ESCALATION_THRESHOLD)
    └── src.models   (Response)
```

**No third-party runtime dependencies.** All modules use only the Python
standard library (`dataclasses`, `random`, `re`). Test dependencies
(`pytest`, `pytest-cov`) are declared as `dev-dependencies` in
`pyproject.toml` and are only required during testing.
