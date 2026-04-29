"""
recommender.py
Core retrieval and scoring logic for Music Recommender AI.
No AI calls here — pure Python. This is the "retrieval" half of RAG.
"""

import csv
import os


def load_songs(filepath=None):
    """Load songs from CSV and convert numeric fields to correct types."""
    if filepath is None:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(base, "data", "songs.csv")

    songs = []
    with open(filepath, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["energy"] = float(row["energy"])
            row["tempo_bpm"] = int(row["tempo_bpm"])
            songs.append(row)
    return songs


def score_song(user_prefs, song):
    """
    Score a single song against user preferences.
    Returns (score: float, reasons: list[str])

    Scoring rules:
      +2.0 for genre match
      +1.5 for mood match
      +0.0 to +1.0 for energy proximity (1 - |gap|)
    """
    score = 0.0
    reasons = []

    # Genre match
    if song["genre"].lower() == user_prefs.get("favorite_genre", "").lower():
        score += 2.0
        reasons.append("genre match (+2.0)")

    # Mood match
    if song["mood"].lower() == user_prefs.get("favorite_mood", "").lower():
        score += 1.5
        reasons.append("mood match (+1.5)")

    # Energy proximity — rewards songs close to target, penalizes far ones
    target_energy = float(user_prefs.get("target_energy", 0.5))
    gap = abs(song["energy"] - target_energy)
    energy_score = round(max(0.0, 1.0 - gap), 2)
    if energy_score > 0:
        score += energy_score
        reasons.append(f"energy similarity (+{energy_score})")

    return round(score, 2), reasons


def recommend_songs(user_prefs, songs, k=5):
    """
    Score all songs, sort by score descending, return top k.
    Each result: {"song": dict, "score": float, "reasons": list}
    """
    scored = []
    for song in songs:
        score, reasons = score_song(user_prefs, song)
        scored.append({"song": song, "score": score, "reasons": reasons})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]
