# 🤖 IBM SkillsBuild Lab Assistant

A modular, test-driven chatbot designed to assist learners in the IBM SkillsBuild
technical lab environment. Built using a Senior AI Engineering workflow, this
project features a weighted intent-matching engine and a smart escalation strategy
for complex student queries.

---

## 🌟 Key Features

- **Weighted Intent Engine** — Prioritises technical platform issues (watsonx, API
  errors) over general conversational noise using a `keyword_length × priority` scoring formula.
- **Smart Escalation** — Automatically flags low-confidence queries (< 25 %) for
  human intervention via the **#lab-support** Slack channel.
- **58-Test Suite** — Comprehensive verification covering student frustration,
  nonsense inputs, multi-intent collisions, and platform-specific edge cases.
- **Modular Architecture** — Strict separation of concerns between Data Models
  (`src/models.py`), Processing Engine (`src/engine.py`), and CLI interface (`main.py`).

---

## 🛠️ Tech Stack

| Layer | Tool |
|---|---|
| Environment & deps | `uv` |
| Testing | `pytest` |
| Workflow | Agentic development via Claude Code |
| Ruleset | Governed by `CLAUDE.md` architecture standards |

---

## 🚀 Quick Start

> Requires [uv](https://docs.astral.sh/uv/) to be installed.

```bash
# Clone and install
git clone https://github.com/sh4wnbk/IBM-skillsbuild-chatbot.git
cd IBM-skillsbuild-chatbot
uv sync --dev

# Run the 58-test suite
uv run pytest

# Launch the assistant
uv run python main.py
```

---

## 🧠 Design Philosophy

This project was built following a **Senior AI Engineering initialisation protocol**.
By establishing a `CLAUDE.md` rulebook before writing any code, the development
process was governed by strict architectural principles:

- **Test-Driven Development (TDD)** — No feature was committed without a
  corresponding edge-case test.
- **AI Usage Transparency** — All core logic includes AI Usage Statements in
  the module docstrings.
- **Constraint-Based Matching** — The bot uses a scoring algorithm
  (`keyword_length × priority`) rather than simple regex to ensure
  high-accuracy intent resolution.

---

## 📄 Documentation

| File | Purpose |
|---|---|
| `ARCHITECTURE.md` | UML Class Diagrams and System Flow |
| `REFLECTION.md` | Mini-Challenge reflection on testing and UX |
| `CLAUDE.md` | Project-specific engineering standards |
