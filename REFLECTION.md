# Reflection — IBM SkillsBuild Assistant Mini-Challenge

## AI Usage Statement

This document was drafted with assistance from Claude (Anthropic) to structure
reflection answers based on the official IBM SkillsBuild documentation and the
challenge requirements. All final answers are the author's own and have been
reviewed for accuracy against the implementation.

---

## Q1: How did you test the chatbot's behaviour?

Testing was conducted at three levels:

**1. Automated unit tests (`pytest`)**
`tests/test_chatbot.py` contains 50+ test methods across 10 classes covering:
- Every intent (access, watsonx, certification, curriculum, community)
- Edge cases: empty strings, whitespace-only, gibberish, off-topic queries
- Frustrated student sentiment (8 dedicated tests in `TestFrustratedStudent`)
- Smart escalation thresholds (`TestSmartEscalation`)
- Response structure invariants (`TestResponseStructure`)

Run with: `uv run pytest`

**2. Manual REPL sessions**
The chatbot was exercised interactively via `uv run python main.py` using:
- Happy paths: "I'm getting a 403 error on watsonx.ai" → `watsonx` intent
- Edge cases: "", "xkjqwzpvmb", "What is the weather?"
- Frustration: "I give up, nothing works"
- Documentation-specific queries: "My badge hasn't arrived after 48 hours"

**3. Confidence score inspection**
The REPL prints `[intent=X, confidence=Y, escalate=Z]` after every response,
making scoring and escalation behaviour observable without reading source code.

---

## Q2: What UX improvements would you make for real students?

Based on the five documentation sources:

- **Did-you-mean suggestions** when `confidence` is between 0.10–0.25: instead
  of jumping straight to a #lab-support escalation, offer "Did you mean: lab
  access / watsonx troubleshooting / badges?" as a quick-pick list.

- **Inline Slack deep-link** in escalation messages: rather than saying "post
  in #lab-support", embed the direct Slack URL so students can join with one
  click without leaving the chatbot.

- **Frustration + intent fusion**: when a frustration signal co-occurs with a
  valid intent keyword (e.g., "I'm so frustrated about my 403 error"), return
  both the empathetic message *and* the relevant watsonx troubleshooting steps
  in one reply, so the student doesn't need to re-ask once calm.

- **48-hour badge status checker**: a small integration that lets students type
  "check my badge status" and receive a personalised Credly status link, since
  the most common certification question is "it's been 48 hours, where is it?"

- **Session memory**: store the active intent per session so follow-up pronouns
  like "what about the token issue?" preserve context without repeating keywords.

---

## Q3: What were the hardest edge cases to handle?

- **Frustration mixed with a real question** (e.g., "I'm so frustrated about
  my 403 error"): the engine correctly prioritises empathy over information by
  intercepting frustration *before* scoring. However, this means the student
  must re-ask once they've been pointed to #lab-support. The ideal solution
  (frustration + intent fusion, above) requires ranking two response types.

- **Low-confidence single-word matches**: short words like "lab" or "token"
  match multiple intents or produce scores far below the escalation threshold.
  The `ESCALATION_THRESHOLD = 0.25` constant was tuned manually by running
  representative queries and inspecting confidence output.

- **403 vs. access vs. watsonx disambiguation**: "I can't access watsonx"
  contains both `access` and `watsonx` keywords. Because `watsonx` has
  priority 3 and `access` has priority 2, watsonx wins — which is the
  correct resolution since 403 errors are specifically a watsonx.ai issue.

- **48-hour wait confusion**: students often phrase this as "it's been two days"
  rather than "48 hours", which doesn't match the keyword. Added both
  `"48 hours"` and `"48h"` as keywords to maximise recall.

---

## Q4: How does the weighted scoring algorithm work?

For each intent, every keyword is checked as a substring of the normalised
input. When a keyword matches, its contribution to the intent's raw score is:

```
contribution = len(keyword) * intent.priority
```

The intent's total raw score is the sum of all contributions. The `confidence`
returned to the caller is then normalised:

```
confidence = min(raw_score / max_possible_score, 1.0)
```

`max_possible_score` is computed once at engine initialisation as the maximum
theoretical score any single intent could achieve if all its keywords matched.

**Why this formula?**
- `len(keyword)` rewards precision: `"403 forbidden"` (13 chars × 3 = 39)
  scores far more than `"403"` (3 chars × 3 = 9), reducing false positives
  from short ambiguous tokens.
- `intent.priority` reflects business importance: watsonx.ai issues (priority 3)
  are amplified because they are the most technically complex and most commonly
  confused with other topics.

**Smart escalation**: when `confidence < ESCALATION_THRESHOLD` (0.25), the
`Response.escalate` flag is set to `True` and a #lab-support prompt is appended
to the response text. This surfaces the community support channel precisely
when the engine is least certain, directing students to humans when automation
would be unreliable.

---

## Q5: What would you add next?

1. **`support` intent** for direct escalation keywords ("contact human",
   "speak to instructor"), routing to the SkillsBuild support URL immediately.
2. **Conversation logging** to SQLite: store `(timestamp, input, intent, confidence)`
   for analytics — e.g., tracking which intents generate the most low-confidence
   responses to prioritise keyword improvements.
3. **REST API** via FastAPI: wrap `ChatEngine.respond()` in a `/chat` POST
   endpoint to power a web-based SkillsBuild chatbot widget.
4. **Spelling correction**: use `difflib.get_close_matches` to fuzzy-match
   misspelled keywords like "watsonxx" → "watsonx" or "credl" → "credly".
5. **Threshold calibration tests**: add a parametrised pytest suite that verifies
   the escalation threshold triggers correctly across a range of confidence
   values, making threshold changes safer.
