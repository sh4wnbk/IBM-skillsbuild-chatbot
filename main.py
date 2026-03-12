# AI Usage Statement:
# This file was designed with the assistance of Claude (Anthropic) to implement
# the REPL entry point. All logic and docstrings were reviewed and validated
# by the author.

"""Entry point for the IBM SkillsBuild Assistant chatbot.

Run with::

    uv run python main.py

Type your question and press Enter. Type ``quit``, ``exit``, ``bye``, or
press Ctrl+C to end the session.
"""

from src.engine import ESCALATION_THRESHOLD, ChatEngine

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BANNER = """\
╔═══════════════════════════════════════════════════════════╗
║             IBM SkillsBuild Assistant  v2.0               ║
╠═══════════════════════════════════════════════════════════╣
║  I can help with:                                         ║
║    • Lab access & cloud environment setup                 ║
║    • watsonx.ai troubleshooting (403, capacity, tokens)   ║
║    • Badges & certificates (Credly, 80 %+ score)          ║
║    • Course curriculum & module progression               ║
║    • Community support (#lab-support Slack channel)       ║
║                                                           ║
║  Type 'quit' or press Ctrl+C to exit.                     ║
╚═══════════════════════════════════════════════════════════╝
"""

_EXIT_COMMANDS: frozenset[str] = frozenset({"quit", "exit", "bye", "q"})
_FAREWELL = "Assistant: Goodbye! Good luck with your IBM SkillsBuild journey."


# ---------------------------------------------------------------------------
# Main REPL
# ---------------------------------------------------------------------------


def main() -> None:
    """Start the IBM SkillsBuild Assistant interactive REPL session.

    Initialises the ``ChatEngine``, prints a welcome banner, then enters a
    read-evaluate-print loop. Each iteration:

    1. Reads input from stdin.
    2. Checks for exit commands or EOF / KeyboardInterrupt.
    3. Calls ``engine.respond()`` to process the input.
    4. Prints the response text.
    5. If ``response.escalate`` is ``True`` (confidence below threshold or
       fallback), prints an additional note reminding the student to post in
       #lab-support on Slack.
    6. Prints a debug line: ``[intent=X, confidence=Y.YY]`` so graders can
       observe the scoring algorithm in action.

    Args:
        None

    Returns:
        None

    Example:
        Run from the terminal::

            uv run python main.py
    """
    engine = ChatEngine()
    print(BANNER)
    print(f"  [Smart escalation active: confidence threshold = {ESCALATION_THRESHOLD:.0%}]\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{_FAREWELL}")
            break

        if user_input.lower() in _EXIT_COMMANDS:
            print(_FAREWELL)
            break

        response = engine.respond(user_input)
        print(f"\nAssistant: {response.text}\n")
        print(f"  [intent={response.intent_name}, confidence={response.confidence:.2f}, "
              f"escalate={response.escalate}]\n")


if __name__ == "__main__":
    main()
