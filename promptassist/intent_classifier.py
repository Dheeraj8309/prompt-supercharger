# promptassist/intent_classifier.py
from __future__ import annotations
from typing import Tuple, Dict, List
import numpy as np
from sentence_transformers import SentenceTransformer, util

_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Add "image" and keep a clear "general" fallback
LABELS: List[str] = [
    "email",
    "rewrite",
    "summarize",
    "translate",
    "code",
    "data",
    "image",
    "general",
]

# Lightweight keyword rules that short-circuit to a label
_KEYWORD_RULES: Dict[str, List[str]] = {
    "image": [
        "image", "picture", "pic", "photo", "photograph", "poster", "banner",
        "thumbnail", "wallpaper", "art", "illustration", "drawing", "sketch",
        "render", "3d", "sticker", "emoji", "logo", "icon", "graphic",
        "cover", "hero image"
    ],
    "email": ["email", "e-mail", "mail", "message", "letter", "inbox", "subject", "recipient"],
    "code": ["code", "python", "java", "js", "javascript", "typescript", "bug", "function", "class", "api"],
    "translate": ["translate", "translation", "to english", "to spanish", "to hindi", "in french"],
    "summarize": ["summarize", "tl;dr", "summary", "briefly"],
    "rewrite": ["rewrite", "paraphrase", "rephrase", "polish"],
    "data": ["csv", "table", "data", "dataset", "chart", "plot", "graph"],
}

_model: SentenceTransformer | None = None
_label_emb = None

def _load_model():
    global _model, _label_emb
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
        _label_emb = _model.encode(LABELS, normalize_embeddings=True)

def _rule_based(text: str) -> Tuple[str, float] | None:
    t = text.lower()
    for label, kws in _KEYWORD_RULES.items():
        if any(k in t for k in kws):
            return label, 0.95
    return None

def classify_intent(text: str) -> Tuple[str, float]:
    """Return (intent, confidence)."""
    if not text or not text.strip():
        return "general", 0.0

    rb = _rule_based(text)
    if rb:
        return rb  # (label, 0.95)

    _load_model()
    v = _model.encode([text], normalize_embeddings=True)
    sim = util.cos_sim(v, _label_emb).cpu().numpy()[0]
    idx = int(np.argmax(sim))
    return LABELS[idx], float(sim[idx])
