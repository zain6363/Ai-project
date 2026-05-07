# ============================================================
#  BATTLE CITY — HIGH SCORE MODULE
#  AL2002 Artificial Intelligence Lab | Spring 2026
# ============================================================

import json
import os
from datetime import datetime

# Path sits next to this file (same project directory)
_DIR        = os.path.dirname(os.path.abspath(__file__))
SCORES_FILE = os.path.join(_DIR, 'highscores.json')
MAX_ENTRIES = 10


# ── I/O helpers ──────────────────────────────────────────────

def load_scores() -> list[dict]:
    """Return the saved leaderboard (sorted high→low). Never raises."""
    if not os.path.exists(SCORES_FILE):
        return []
    try:
        with open(SCORES_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if isinstance(data, list):
            return sorted(data, key=lambda x: x.get('score', 0), reverse=True)
    except Exception:
        pass
    return []


def _write_scores(scores: list[dict]) -> None:
    try:
        with open(SCORES_FILE, 'w', encoding='utf-8') as f:
            json.dump(scores, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


# ── Public API ────────────────────────────────────────────────

def save_score(score: int, difficulty: str,
               level_reached: int, won: bool) -> int:
    """
    Persist a new score entry and return its 0-based rank index
    in the updated leaderboard (or -1 if it didn't make the board).
    """
    entry = {
        'score':      score,
        'difficulty': difficulty,
        'level':      level_reached,
        'won':        won,
        'date':       datetime.now().strftime('%d %b %Y'),
    }
    scores = load_scores()
    scores.append(entry)
    scores.sort(key=lambda x: x.get('score', 0), reverse=True)
    scores = scores[:MAX_ENTRIES]
    _write_scores(scores)

    # Find the rank of our entry
    for i, s in enumerate(scores):
        if (s['score'] == score and s['difficulty'] == difficulty
                and s['level'] == level_reached and s['won'] == won
                and s['date'] == entry['date']):
            return i
    return -1


def is_high_score(score: int) -> bool:
    """True if this score would appear on the leaderboard."""
    scores = load_scores()
    if len(scores) < MAX_ENTRIES:
        return True
    return score > scores[-1].get('score', 0)


def clear_scores() -> None:
    """Wipe the leaderboard (used for testing)."""
    _write_scores([])
