# promptassist/vocab.py
from __future__ import annotations
import os

# small manual fallback list so you always return something
_FALLBACK = {
    "email": ["mail", "message", "letter"],
    "professor": ["teacher", "instructor", "lecturer"],
    "formal": ["professional", "official", "academic"],
    "friendly": ["casual", "warm", "approachable"],
    "concise": ["short", "brief", "to the point"],
}

# Try to load WordNet safely in local dir
wn = None
try:
    import nltk
    from nltk.corpus import wordnet as _wn
    _DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "nltk_data")
    os.makedirs(_DATA_DIR, exist_ok=True)
    nltk.data.path.insert(0, _DATA_DIR)
    try:
        _ = _wn.synsets("test")
        wn = _wn
    except LookupError:
        nltk.download("wordnet", download_dir=_DATA_DIR, quiet=True)
        nltk.download("omw-1.4", download_dir=_DATA_DIR, quiet=True)
        from nltk.corpus import wordnet as _wn
        _ = _wn.synsets("test")
        wn = _wn
except Exception:
    wn = None


def _wn_syns(word: str) -> set[str]:
    if not wn:
        return set()
    out: set[str] = set()
    try:
        for s in wn.synsets(word):
            for l in s.lemmas():
                out.add(l.name().replace("_", " ").lower())
    except Exception:
        pass
    return out


def vocab_boosts(text: str):
    """Return a list of {word, alternatives[]} for a few important words."""
    boosts = []
    for w, fb in _FALLBACK.items():
        alts = set(fb) | _wn_syns(w)
        boosts.append({"word": w, "alternatives": sorted(alts)[:30]})
    return boosts
