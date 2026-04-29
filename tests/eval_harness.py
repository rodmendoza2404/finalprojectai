"""
eval_harness.py
Automated evaluation script for Music Recommender AI.

Runs predefined test cases and prints a pass/fail summary.
Tests run against the LIVE Claude API — make sure .env is configured.

Usage:
    python tests/eval_harness.py

Stretch feature: Test Harness (+2 pts)
"""

import os
import sys

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.recommender import load_songs
from src.rag_engine import rag_recommend, CONFIDENCE_THRESHOLD

# ── Test Cases ────────────────────────────────────────────────────────────────
# Each case has:
#   name         : display label
#   query        : plain-English input
#   expect_status: "success" or "no_match"
#   expect_genre : (optional) genre Claude should extract
#   expect_mood  : (optional) mood Claude should extract
#   expect_energy_min: (optional) minimum target_energy extracted
#   expect_top_score_min: (optional) minimum score for #1 result

TEST_CASES = [
    {
        "name": "Chill Study Session",
        "query": "I want something chill and relaxing for studying",
        "expect_status": "success",
        "expect_mood": "chill",
        "expect_energy_max": 0.4,
    },
    {
        "name": "High Energy Workout",
        "query": "Give me high energy music to pump me up at the gym",
        "expect_status": "success",
        "expect_energy_min": 0.65,
    },
    {
        "name": "Happy Pop Vibes",
        "query": "I'm in a great mood, I want happy pop music",
        "expect_status": "success",
        "expect_genre": "pop",
        "expect_mood": "happy",
    },
    {
        "name": "Sad Rainy Day",
        "query": "Something melancholy and slow for a sad rainy afternoon",
        "expect_status": "success",
        "expect_mood": "sad",
    },
    {
        "name": "Jazz Focus",
        "query": "Some jazz music to help me focus while I work",
        "expect_status": "success",
        "expect_genre": "jazz",
    },
    {
        "name": "Guardrail — Vague Request",
        "query": "just play something",
        "expect_status": "no_match",   # too vague → low scores → guardrail fires
    },
]


def run_case(tc: dict, songs: list) -> tuple[bool, list[str]]:
    """Run one test case. Returns (passed: bool, check_lines: list[str])."""
    result = rag_recommend(tc["query"], songs)
    status = result.get("status")
    checks = []
    all_pass = True

    # Status check (always required)
    if status == tc["expect_status"]:
        checks.append(f"  ✅ status = '{status}'")
    else:
        checks.append(f"  ❌ status: expected '{tc['expect_status']}', got '{status}'")
        all_pass = False

    if status == "success":
        prefs = result.get("prefs", {})
        top = result["top_songs"]

        if "expect_genre" in tc:
            got = prefs.get("favorite_genre", "")
            if got == tc["expect_genre"]:
                checks.append(f"  ✅ genre extracted = '{got}'")
            else:
                checks.append(f"  ❌ genre: expected '{tc['expect_genre']}', got '{got}'")
                all_pass = False

        if "expect_mood" in tc:
            got = prefs.get("favorite_mood", "")
            if got == tc["expect_mood"]:
                checks.append(f"  ✅ mood extracted = '{got}'")
            else:
                checks.append(f"  ❌ mood: expected '{tc['expect_mood']}', got '{got}'")
                all_pass = False

        if "expect_energy_min" in tc:
            val = float(prefs.get("target_energy", 0))
            if val >= tc["expect_energy_min"]:
                checks.append(f"  ✅ energy {val} >= {tc['expect_energy_min']}")
            else:
                checks.append(f"  ❌ energy: expected >= {tc['expect_energy_min']}, got {val}")
                all_pass = False

        if "expect_energy_max" in tc:
            val = float(prefs.get("target_energy", 1))
            if val <= tc["expect_energy_max"]:
                checks.append(f"  ✅ energy {val} <= {tc['expect_energy_max']}")
            else:
                checks.append(f"  ❌ energy: expected <= {tc['expect_energy_max']}, got {val}")
                all_pass = False

        if top:
            checks.append(f"  ℹ️  Top song: \"{top[0]['song']['title']}\" (score {top[0]['score']:.2f})")

    if status == "no_match" and tc["expect_status"] == "no_match":
        checks.append(f"  ✅ guardrail correctly fired (score below {CONFIDENCE_THRESHOLD})")

    return all_pass, checks


def run_eval():
    songs = load_songs()

    print("=" * 62)
    print("  MUSIC RECOMMENDER AI — EVALUATION HARNESS")
    print(f"  {len(songs)} songs loaded  |  {len(TEST_CASES)} test cases")
    print("=" * 62)

    passed = 0
    failed = 0

    for tc in TEST_CASES:
        print(f"\n📋  {tc['name']}")
        print(f"    Query: \"{tc['query']}\"")

        ok, checks = run_case(tc, songs)
        for line in checks:
            print(line)

        if ok:
            passed += 1
            print("  → PASS")
        else:
            failed += 1
            print("  → FAIL")

    print("\n" + "=" * 62)
    print(f"  RESULTS: {passed}/{len(TEST_CASES)} passed")
    pct = passed / len(TEST_CASES) * 100
    print(f"  Score:   {pct:.0f}%  {'🟢' if pct >= 80 else '🟡' if pct >= 60 else '🔴'}")
    print("=" * 62)


if __name__ == "__main__":
    run_eval()
