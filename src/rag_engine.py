"""
rag_engine.py
RAG pipeline: natural language query → structured prefs → retrieve → guardrail → generate.

Two Claude API calls per request:
  1. parse_query()    — extract structured preferences from plain English
  2. generate_recommendation() — explain top results using ONLY retrieved songs
"""

import os
import json
import logging
import anthropic

from src.recommender import load_songs, recommend_songs

# Minimum score the top song must have before we attempt generation.
# Below this threshold, the guardrail fires and refuses to answer.
CONFIDENCE_THRESHOLD = 1.5
DEFAULT_CLAUDE_MODEL = "claude-haiku-4-5"

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


def _get_client():
    """Return Anthropic client, raising a clear error if key is missing."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY not found. "
            "Create a .env file with: ANTHROPIC_API_KEY=your_key_here"
        )
    return anthropic.Anthropic(api_key=api_key)


def _get_model_name() -> str:
    """Return the Claude model name, allowing local override via environment."""
    return os.environ.get("ANTHROPIC_MODEL", DEFAULT_CLAUDE_MODEL)


def parse_query(query: str) -> dict:
    """
    Use Claude to extract structured music preferences from a plain-English query.
    Returns a dict with keys: favorite_genre, favorite_mood, target_energy.
    """
    client = _get_client()

    prompt = f"""Extract music preferences from this query. Respond ONLY with a JSON object — no explanation, no markdown fences.

Query: "{query}"

Return exactly this structure:
{{
  "favorite_genre": "<one of: pop, rock, lofi, jazz, electronic, hip-hop, classical, country, r&b, metal>",
  "favorite_mood": "<one of: happy, sad, chill, energetic, romantic, angry, focused, party>",
  "target_energy": <float 0.0 to 1.0>
}}"""

    log.info("Calling Claude to parse query...")
    response = client.messages.create(
        model=_get_model_name(),
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = "".join(
        str(getattr(block, "text", ""))
        for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip()
    # Strip accidental markdown fences
    raw = raw.replace("```json", "").replace("```", "").strip()

    prefs = json.loads(raw)
    log.info(f"Parsed preferences: {prefs}")
    return prefs


def generate_recommendation(query: str, top_songs: list) -> str:
    """
    Ask Claude to write a grounded recommendation using ONLY the retrieved songs.
    The prompt explicitly forbids inventing songs not in the list.
    """
    client = _get_client()

    song_list = "\n".join([
        f'- "{r["song"]["title"]}" by {r["song"]["artist"]} '
        f'(genre: {r["song"]["genre"]}, mood: {r["song"]["mood"]}, '
        f'energy: {r["song"]["energy"]}) '
        f'[{", ".join(r["reasons"])}]'
        for r in top_songs
    ])

    prompt = f"""You are a music recommendation assistant. A user asked: "{query}"

Here are the songs retrieved from our catalog that best match their preferences:
{song_list}

Write a friendly 2-3 sentence recommendation using ONLY the songs above.
Reference specific song titles and explain why they match.
Do NOT suggest any songs not listed above."""

    log.info("Calling Claude to generate explanation...")
    response = client.messages.create(
        model=_get_model_name(),
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )

    return "".join(
        str(getattr(block, "text", ""))
        for block in response.content
        if getattr(block, "type", None) == "text"
    ).strip()


def rag_recommend(query: str, songs: list | None = None, k: int = 5) -> dict:
    """
    Full RAG pipeline:
      1. Parse natural language query → structured prefs (Claude)
      2. Score and retrieve top-k songs (pure Python)
      3. Guardrail: refuse if top score < CONFIDENCE_THRESHOLD
      4. Generate grounded explanation (Claude, grounded in retrieved songs only)

    Returns a dict with keys:
      status: "success" | "no_match" | "error"
      prefs, top_songs, explanation (on success)
      message (on no_match or error)
    """
    if songs is None:
        songs = load_songs()

    # Step 1: Parse
    try:
        prefs = parse_query(query)
    except json.JSONDecodeError as e:
        return {"status": "error", "message": f"Could not parse AI response as JSON: {e}"}
    except EnvironmentError as e:
        return {"status": "error", "message": str(e)}
    except Exception as e:
        return {"status": "error", "message": f"Unexpected error during parsing: {e}"}

    # Step 2: Retrieve
    top_songs = recommend_songs(prefs, songs, k=k)

    # Step 3: Guardrail — refuse if confidence is too low
    if not top_songs or top_songs[0]["score"] < CONFIDENCE_THRESHOLD:
        log.warning(f"Guardrail triggered. Top score: {top_songs[0]['score'] if top_songs else 0}")
        return {
            "status": "no_match",
            "message": (
                "I couldn't find a strong match for your request. "
                "Try specifying a genre (e.g. 'lofi', 'rock') or a mood (e.g. 'chill', 'energetic')."
            ),
            "prefs": prefs,
            "top_songs": top_songs,
        }

    # Step 4: Generate
    try:
        explanation = generate_recommendation(query, top_songs)
    except Exception as e:
        return {
            "status": "error",
            "message": f"Retrieval succeeded but generation failed: {e}",
            "prefs": prefs,
            "top_songs": top_songs,
        }

    return {
        "status": "success",
        "prefs": prefs,
        "top_songs": top_songs,
        "explanation": explanation,
    }
