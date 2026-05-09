"""
Follow-up Suggestion Generator
After every answer, uses Groq to generate 3 smart, context-aware
follow-up questions the user might want to ask next.

Strategy:
- Sends the Q&A pair + document context to Groq
- Returns 3 short, distinct, clickable follow-up questions
- Runs async (non-blocking) so it doesn't slow down the main answer
"""

import os
import json
import logging
from typing import List, Optional
from groq import Groq

logger = logging.getLogger(__name__)

_client = None
def get_client():
    global _client
    if _client is None:
        _client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


# ─────────────────────────────────────────────
# System prompt
# ─────────────────────────────────────────────

FOLLOWUP_SYSTEM_PROMPT = """You are a helpful assistant that generates follow-up questions.

Given a question, an answer, and document context, generate exactly 3 short follow-up questions the user might logically want to ask next.

Rules:
- Each question must be SHORT (max 10 words)
- Questions must be DIFFERENT from each other — cover different angles
- Questions must be ANSWERABLE from the document context provided
- Do NOT repeat or rephrase the original question
- Do NOT start all questions the same way
- Return ONLY a JSON array of 3 strings, nothing else

Example output:
["What caused this decline?", "How does Q4 compare?", "Which region performed best?"]
"""


# ─────────────────────────────────────────────
# Generator function
# ─────────────────────────────────────────────

def generate_followup_suggestions(
    question: str,
    answer: str,
    context_chunks: List[dict],
    model: str = "llama-3.1-8b-instant",   # fast model, suggestions don't need 70B
    max_suggestions: int = 3,
) -> List[str]:
    """
    Generate follow-up question suggestions based on the Q&A and document context.

    Args:
        question:       The user's original question.
        answer:         The AI's answer.
        context_chunks: Retrieved chunks used to generate the answer.
        model:          Groq model (use fast model — 8B is sufficient).
        max_suggestions: Number of suggestions to return.

    Returns:
        List of follow-up question strings.
    """
    if not question or not answer:
        return []

    # Build a short context summary (first 600 chars of top chunks)
    context_preview = ""
    for chunk in context_chunks[:3]:
        context_preview += f"- {chunk.get('text', '')[:200]}\n"

    user_message = f"""Original question: {question}

Answer given: {answer[:500]}

Document context snippets:
{context_preview}

Generate {max_suggestions} follow-up questions."""

    try:
        client = get_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": FOLLOWUP_SYSTEM_PROMPT},
                {"role": "user",   "content": user_message},
            ],
            max_tokens=150,
            temperature=0.7,          # some creativity for variety
            response_format={"type": "json_object"},
        )

        raw = response.choices[0].message.content.strip()

        # Parse JSON — handle both array and object with array value
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            suggestions = parsed
        elif isinstance(parsed, dict):
            # Model may wrap: {"questions": [...]} or {"suggestions": [...]}
            suggestions = next(
                (v for v in parsed.values() if isinstance(v, list)), []
            )
        else:
            suggestions = []

        # Clean up and limit
        suggestions = [
            s.strip().rstrip("?") + "?" if not s.strip().endswith("?") else s.strip()
            for s in suggestions
            if isinstance(s, str) and s.strip()
        ]

        return suggestions[:max_suggestions]

    except json.JSONDecodeError as e:
        logger.warning(f"Follow-up JSON parse error: {e}")
        return _fallback_suggestions(question, answer)
    except Exception as e:
        logger.error(f"Follow-up generation failed: {e}")
        return []


# ─────────────────────────────────────────────
# Fallback rule-based suggestions
# ─────────────────────────────────────────────

def _fallback_suggestions(question: str, answer: str) -> List[str]:
    """
    Simple rule-based fallback if Groq call fails.
    Generates generic but relevant follow-up starters.
    """
    starters = [
        "Can you explain this in more detail?",
        "What are the main reasons for this?",
        "How does this compare to previous periods?",
    ]
    return starters
