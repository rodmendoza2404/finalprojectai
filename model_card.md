# Model Card — Music Recommender AI (VibeFinder RAG 2.0)

## Model Name
VibeFinder RAG 2.0

---

## Goal / Task
Take a plain-English music request (e.g., "something chill for studying") and return a ranked list of matching songs with a grounded, explained recommendation. The system is designed to simulate how a content-based music recommender works at a small scale, with a RAG layer that grounds the AI's explanations in actual retrieved data.

---

## Data Used
- **Source:** Custom CSV catalog (`data/songs.csv`)
- **Size:** 20 songs
- **Features per song:** title, artist, genre, mood, energy (0.0–1.0), tempo_bpm
- **Genre distribution:** pop (5), lofi (4), rock (4), hip-hop (3), jazz (3), classical (1)
- **Mood distribution:** chill (4), energetic (3), happy (3), angry (2), focused (2), sad (1), romantic (2), party (1)
- **Limitation:** Dataset is heavily skewed toward pop and lofi. Users with niche preferences (e.g., country, metal) will consistently get low-confidence results or guardrail refusals.

---

## Algorithm Summary (Plain Language)

**Step 1 — Parse (Claude):**  
The user's plain-English request is sent to Claude, which extracts structured preferences: a genre (e.g., "lofi"), a mood (e.g., "chill"), and a target energy level (0.0–1.0). Claude returns this as JSON.

**Step 2 — Retrieve (Pure Python):**  
Every song in the catalog is scored:
- +2.0 points if the genre matches
- +1.5 points if the mood matches
- +0.0 to +1.0 based on how close the song's energy is to the target

Songs are ranked by score, and the top 5 are selected.

**Step 3 — Guardrail (Rule-based):**  
If the top song's score is below 1.5, the system refuses to answer and asks the user to be more specific. This prevents weak, low-confidence recommendations.

**Step 4 — Generate (Claude):**  
Claude receives the top 5 retrieved songs and the original query, and writes a 2-3 sentence recommendation using only those songs. The prompt explicitly forbids Claude from inventing songs not in the list.

---

## Observed Behavior and Biases

**Filter bubble effect:** Because genre carries the highest weight (+2.0), users who specify "lofi" will almost always receive lofi songs, even if their mood or energy preference might be better served by jazz or classical. The system does not surface surprising-but-relevant cross-genre suggestions.

**Pop dominance:** 5 of 20 songs are pop. Users with ambiguous genre preferences (e.g., "happy and upbeat") frequently receive pop results even if they might enjoy other genres.

**Mood/energy overlap:** "Focused" and "chill" moods often produce similar results because both map to low-energy songs. The system currently cannot distinguish between "calm background music" and "deep concentration mode."

**Language sensitivity:** Claude's query parser performs well on clear English but can misinterpret slang or highly stylized input (e.g., "fire beats" might parse as energetic/hip-hop even if the user meant something else).

---

## Evaluation Process

Six test cases were run using the automated evaluation harness (`tests/eval_harness.py`):

| Test Case | Query | Expected | Result |
|---|---|---|---|
| Chill Study Session | "something chill for studying" | success, mood=chill | ✅ PASS |
| High Energy Workout | "pump me up for the gym" | success, energy≥0.65 | ✅ PASS |
| Happy Pop Vibes | "happy pop music" | success, genre=pop, mood=happy | ✅ PASS |
| Sad Rainy Day | "sad slow music for rainy afternoon" | success, mood=sad | ✅ PASS |
| Jazz Focus | "jazz to help me focus" | success, genre=jazz | ✅ PASS |
| Guardrail Test | "just play something" | no_match (guardrail) | ✅ PASS |

**Overall: 5–6/6 (83–100%)** depending on Claude's parse behavior on the vague input test.

---

## Intended Use
- Educational demonstration of RAG architecture
- Showing how retrieval and generation can be separated and combined responsibly
- Portfolio project demonstrating AI system design

## Non-Intended Use
- Production music service (dataset is too small and unrepresentative)
- Recommending music for users with accessibility or emotional sensitivity needs (no content warnings)
- Any use case requiring real-time performance (latency ~2–4 seconds per request)

---

## Ideas for Improvement

1. **Hybrid filtering:** Add a mock "users who liked X also liked Y" layer to break genre filter bubbles and surface cross-genre discoveries.

2. **Larger, more diverse dataset:** 20 songs is not enough for real variety. A 200+ song dataset with balanced genre and mood distribution would significantly improve recommendation quality.

3. **Confidence explanation to user:** Instead of just saying "no match," tell the user specifically what was close (e.g., "I found some chill songs but none matched your genre preference — showing closest results anyway").

---

## AI Collaboration Notes

**Helpful AI suggestion:** When designing the JSON extraction prompt, Copilot suggested adding explicit enum constraints ("one of: pop, rock, lofi…") directly inside the prompt string. This dramatically reduced parse errors because Claude was less likely to invent genre names not in the catalog.

**Flawed AI suggestion:** An early version of `score_song()` generated by Copilot used exponential decay for the energy score (`math.exp(-gap * 5)`). While mathematically elegant, this produced scores in a range (0.007–1.0) that made calibrating the confidence threshold nearly impossible. I replaced it with the simpler linear formula `max(0.0, 1.0 - gap)` which is easier to reason about and calibrate.

**What I learned:** AI-generated code often optimizes for sophistication over interpretability. For a system where you need to tune thresholds and debug scoring, readable math beats clever math every time.
