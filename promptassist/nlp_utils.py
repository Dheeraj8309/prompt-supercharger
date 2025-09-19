# promptassist/nlp_utils.py
from __future__ import annotations
import os, re

# --- optional built-in synonyms as a fallback ---
FALLBACK = {
    "email": ["mail", "message", "letter"],
    "professor": ["teacher", "instructor", "lecturer"],
    "formal": ["professional", "official", "academic"],
    "friendly": ["casual", "warm", "approachable"],
    "concise": ["short", "brief", "to the point"],
}

# Try to make WordNet available in a local data dir
_WN = None
try:
    import nltk
    from nltk.corpus import wordnet as _wn

    _DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "nltk_data")
    os.makedirs(_DATA_DIR, exist_ok=True)
    nltk.data.path.insert(0, _DATA_DIR)

    try:
        # Will raise LookupError if not downloaded
        _ = _wn.synsets("test")
        _WN = _wn
    except LookupError:
        # Download once into local dir
        nltk.download("wordnet", download_dir=_DATA_DIR, quiet=True)
        nltk.download("omw-1.4", download_dir=_DATA_DIR, quiet=True)
        from nltk.corpus import wordnet as _wn  # reload after download
        _ = _wn.synsets("test")  # try again
        _WN = _wn
except Exception:
    # If anything goes wrong, we just proceed without WordNet
    _WN = None


def _wordnet_synonyms(word: str) -> set[str]:
    """Collect synonyms for a word from WordNet (if available)."""
    if not _WN:
        return set()
    syns: set[str] = set()
    try:
        for s in _WN.synsets(word):
            for l in s.lemmas():
                syns.add(l.name().replace("_", " ").lower())
    except Exception:
        pass
    return syns


def normalize_terms(text: str) -> str:
    """
    Replace synonyms with canonical words for consistency (case-insensitive).
    Uses WordNet when available, falls back to a small built-in map.
    """
    lowered = text.lower()

    # Build a replacement table: {canonical: {all synonyms}}
    canon_to_syns: dict[str, set[str]] = {}
    for canon, fb_syns in FALLBACK.items():
        all_syns = set(fb_syns) | {canon}
        all_syns |= _wordnet_synonyms(canon)  # add WordNet cluster
        # longest-first replacement avoids partial overlaps
        canon_to_syns[canon] = set(sorted(all_syns, key=len, reverse=True))

    # Do whole-word replacements
    for canon, syns in canon_to_syns.items():
        for syn in syns:
            pattern = r"\b" + re.escape(syn) + r"\b"
            lowered = re.sub(pattern, canon, lowered, flags=re.IGNORECASE)

    return lowered
