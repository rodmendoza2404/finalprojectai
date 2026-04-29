"""
main.py
CLI entry point for Music Recommender AI.

Usage:
    python -m src.main
"""

import os
from dotenv import load_dotenv

load_dotenv()

from src.recommender import load_songs
from src.rag_engine import rag_recommend


DIVIDER = "─" * 60


def print_result(result: dict):
    """Pretty-print a RAG recommendation result."""
    status = result.get("status")

    if status == "error":
        print(f"\n❌  Error: {result['message']}")
        return

    if status == "no_match":
        print(f"\n⚠️   No strong match found.")
        print(f"     {result['message']}")
        print(f"     Extracted preferences: {result.get('prefs', {})}")
        if result.get("top_songs"):
            print(f"     Best score found: {result['top_songs'][0]['score']:.2f} (threshold: 1.5)")
        return

    # Success
    prefs = result["prefs"]
    print(f"\n✅  Preferences extracted:")
    print(f"    Genre: {prefs.get('favorite_genre')}  |  "
          f"Mood: {prefs.get('favorite_mood')}  |  "
          f"Energy target: {prefs.get('target_energy')}")

    print(f"\n🎵  Top {len(result['top_songs'])} Matches:")
    for i, r in enumerate(result["top_songs"], 1):
        s = r["song"]
        print(f"  {i}. \"{s['title']}\" by {s['artist']}")
        print(f"     Score: {r['score']:.2f} | Energy: {s['energy']} | "
              f"Reasons: {', '.join(r['reasons'])}")

    print(f"\n💬  AI Recommendation:")
    # Wrap explanation at 70 chars for readability
    words = result["explanation"].split()
    line = "    "
    for word in words:
        if len(line) + len(word) + 1 > 74:
            print(line)
            line = "    " + word + " "
        else:
            line += word + " "
    if line.strip():
        print(line)


def main():
    songs = load_songs()
    print(f"\n🎧  Music Recommender AI  |  {len(songs)} songs loaded")
    print(f"    Powered by Claude (RAG pipeline)\n")
    print("    Describe what you want in plain English.")
    print("    Examples:")
    print('      "Something chill for studying late at night"')
    print('      "High energy music for my workout"')
    print('      "Sad songs for a rainy Sunday"')
    print("\n    Type 'quit' to exit.\n")
    print(DIVIDER)

    while True:
        try:
            query = input("\nYour request: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit", "q"):
            print("Bye!")
            break

        print("\n⏳  Processing...")
        result = rag_recommend(query, songs)
        print_result(result)
        print(f"\n{DIVIDER}")


if __name__ == "__main__":
    main()
