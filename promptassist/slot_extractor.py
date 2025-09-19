# promptassist/slot_extractor.py
from __future__ import annotations
from typing import Tuple, Set, Dict
import re

# very small stoplist just to ignore glue words
STOPWORDS: Set[str] = {
    "a","an","the","this","that","my","your","his","her","its","our","their",
    "for","about","on","in","at","of","with","and","or","to","from","by",
    "please","need","want","make","create","generate","draw","design","build",
    "give","show","me","us"
}

# normalize a few common synonyms
SUBJECT_NORMALIZE: Dict[str, str] = {
    "bicycle": "bike",
    "cycle": "bike",
    "motorbike": "motorcycle",
    "plane": "airplane",
    "carriage": "car",
    "photo": "image",
    "picture": "image",
    "pic": "image",
}

CATEGORIES: Dict[str, set] = {
    "animal": {
        "bird","dog","cat","lion","tiger","elephant","horse","eagle","sparrow",
        "owl","fox","wolf","bear","fish","shark","panda","monkey","butterfly"
    },
    "vehicle": {
        "bike","bmx","bicycle","motorcycle","car","bus","truck","train",
        "airplane","boat","ship","scooter","van","jeep","bicycle","cycle"
    },
    "person": {
        "person","man","woman","boy","girl","student","teacher","professor",
        "child","kids","adult","model"
    },
    "scene": {
        "mountain","beach","forest","desert","city","street","sky","sunset",
        "waterfall","park","room","kitchen","office","stadium","temple"
    },
    "food": {
        "pizza","burger","sandwich","cake","coffee","tea","sushi","noodles",
        "pasta","salad","icecream","ice-cream"
    },
}

def _norm(tok: str) -> str:
    tok = tok.lower()
    return SUBJECT_NORMALIZE.get(tok, tok)

def extract_subject(text: str) -> Tuple[str, str]:
    """
    Returns (subject, category). Category is one of:
    vehicle/animal/person/scene/food/object
    """
    tokens = re.findall(r"[a-zA-Z\-]+", text.lower())
    candidates = [t for t in tokens if t not in STOPWORDS]

    subject = ""
    # prefer the last meaningful word (often the head)
    for t in reversed(candidates):
        t = _norm(t)
        # pick category if we recognize it
        for cat, vocab in CATEGORIES.items():
            if t in vocab:
                return t, cat
        if not subject:
            subject = t

    # fallback
    return (subject or (candidates[-1] if candidates else "")), "object"
