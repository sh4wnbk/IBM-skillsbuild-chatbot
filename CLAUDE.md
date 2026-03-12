# Project Guidelines: SkillsBuild Chatbot Challenge

## 1. Goal: IBM SkillsBuild Assistant
- Implement 3+ intents (Access, watsonx, Certification).
- Implement a helpful fallback strategy.
- Provide a modular Python program (src/models.py, src/engine.py, main.py).

## 2. Documentation & Reflection
- Create 'REFLECTION.md': Answer the testing/UX questions from the challenge.
- Create 'ARCHITECTURE.md': Include a text-based UML Class Diagram.
- Every file must have "AI Usage Statements" and Google-style docstrings.

## 3. Engineering Standards
- Use 'uv' for dependencies and 'pytest' for testing.
- Implement weighted scoring (keyword length * priority).
- Handle edge cases: empty input, nonsense, and student frustration.

## 4. Commands
- Test: uv run pytest
- Run: uv run python main.py

## 5. Web Interface (GitHub Pages)
- Standard: Single-file `index.html` in the root for easy GitHub Pages deployment.
- Styling: Tailwind CSS (via CDN) for a professional IBM-themed UI.
- Logic: Port the Python scoring algorithm (`keyword_length * priority`) exactly to JavaScript.
- Icons: Use Lucide icons for UI elements.
