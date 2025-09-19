# promptassist/suggestion_engine.py
from typing import List, Dict, Tuple
import re

# Optional classifier (graceful fallback if missing)
try:
    from .intent_classifier import classify_intent  # returns (intent, confidence)
except Exception:
    classify_intent = None


# -------------------- Intent & UI metadata --------------------

VARIATIONS = {
    "email": ["More formal.", "Friendlier but professional.", "Very concise (80–100 words)."],
    "image": ["Photorealistic style.", "Minimal flat illustration.", "Watercolor painting.",
              "Isometric 3D render.", "Pixel art / retro."],
    "code":  ["Idiomatic style.", "Heavy inline comments.", "Performance-optimized."],
    "general": ["More formal.", "Friendlier.", "Very concise (1–2 sentences)."]
}

CLARIFY = {
    "email": [
        "Who is the recipient and their role?",
        "What is the purpose (inform, request, update)?",
        "Preferred tone (formal, friendly, concise)?",
        "Any constraints (length, deadline)?",
    ],
    "image": [
        "What is the main subject and its key attributes?",
        "Style (photo, 3D render, illustration, watercolor, pixel art, etc.)?",
        "Background/setting for the image?",
        "Composition & aspect ratio (close-up vs wide; 1:1, 4:5, 16:9)?",
        "Lighting / mood (golden hour, studio softbox, neon, moody, high-key)?",
        "Any color palette or reference keywords?",
    ],
    "code": [
        "Preferred programming language or framework?",
        "What should the code do (task/goal)?",
        "What inputs does it take (format, examples)?",
        "What should it output/return?",
        "Any constraints (performance, style, error handling)?",
        "Runtime environment / versions / packages to use/avoid?",
    ],
    "general": [
        "What outcome do you want?",
        "Any constraints or preferences?",
        "Who is the target audience?",
    ],
}


# -------------------- Small helpers (no external deps) --------------------

def _answers_to_map(answers: List[Dict[str, str]]) -> Dict[str, str]:
    m: Dict[str, str] = {}
    for a in answers or []:
        name = str(a.get("name", "")).strip().lower()
        val = str(a.get("value", "")).strip()
        if name and val:
            m[name] = val
    return m


def _intent_for_text(text: str) -> Tuple[str, float]:
    """Use your classifier if present; otherwise heuristic fallback."""
    if classify_intent is not None:
        try:
            intent, conf = classify_intent(text)
            # keep it to the three core intents when possible
            if intent not in {"image", "email", "code"}:
                intent = _heuristic_intent(text)
            return intent, conf
        except Exception:
            pass
    return _heuristic_intent(text), 0.5


def _heuristic_intent(text: str) -> str:
    t = (text or "").lower()
    if any(w in t for w in ["image", "photo", "render", "illustration", "icon", "logo", "picture"]):
        return "image"
    if any(w in t for w in ["email", "mail", "message", "professor", "manager", "recipient"]):
        return "email"
    if any(w in t for w in ["code", "function", "script", "class", "api", "python", "javascript", "java", "c++"]):
        return "code"
    return "general"


def _normalize_comp(comp: str) -> Tuple[str, str | None]:
    comp = (comp or "").strip()
    ratio = None
    m = re.search(r"\b(\d+:\d+)\b", comp)
    if m:
        ratio = m.group(1)
        comp = comp.replace(ratio, "").strip(",; .")
    comp = comp.replace("close up", "close-up")
    return comp, ratio


def _choose_prep(bg: str) -> str:
    bg_l = (bg or "").lower()
    on_words = ["street", "road", "highway", "bridge", "beach", "field", "roof", "snow", "ice", "sand"]
    return "on" if any(w in bg_l for w in on_words) else "in"


def _article(word: str) -> str:
    if not word:
        return "a"
    return "an" if word.strip().lower()[0] in "aeiou" else "a"


# -------------------- First-pass: /api/suggest --------------------

def _improved_prompt(intent: str, text: str) -> str:
    if intent == "image":
        return (
            "Role: image prompt engineer.\n"
            "Goal: Create a high-quality prompt for an image generator.\n"
            f"Inputs: {text}.\n"
            "Constraints: include subject, style, composition, background, lighting, color palette; "
            "add aspect ratio if provided. Output: a single concise, natural sentence suitable for an image model.\n"
        )
    if intent == "email":
        return (
            "Role: email assistant.\n"
            "Goal: Draft a professional email that satisfies the request.\n"
            f"Inputs: {text}.\n"
            "Constraints: 120–150 words, professional tone, clear structure.\n"
            "Output: plain text only.\n"
        )
    if intent == "code":
        return (
            "Role: coding assistant.\n"
            "Goal: Write correct, readable code to satisfy the request.\n"
            f"Inputs: {text}.\n"
            "Constraints: include function signature, inputs, outputs, and minimal examples if helpful.\n"
            "Output: code block only.\n"
        )
    # Fallback (should rarely appear in your UI now)
    return (
        "Role: helpful assistant.\n"
        "Goal: Fulfill the request clearly and concisely.\n"
        f"Inputs: {text}.\n"
        "Constraints: be specific, avoid disclaimers, ask 2–3 brief clarifying questions if details are missing.\n"
        "Output: plain text only.\n"
    )


def suggest(text: str, lang: str = "en") -> Dict:
    intent, conf = _intent_for_text(text)

    # lock the UI to the three intents, but keep a safe general fallback
    if intent not in CLARIFY:
        intent = "general"

    improved = _improved_prompt(intent, text)
    clarifying = CLARIFY.get(intent, CLARIFY["general"])
    variations = VARIATIONS.get(intent, VARIATIONS["general"])

    slots = {
        "tone": "formal" if intent == "email" else None,
        "format": None,
        "goal": (
            "Draft an image prompt." if intent == "image" else
            "Draft a professional email." if intent == "email" else
            "Write code." if intent == "code" else
            "Complete the task."
        ),
        "inputs": text,
        "length": "120–150 words" if intent == "email" else None,
        "audience": None,
    }

    return {
        "clarifying_questions": clarifying,
        "confidence": round(float(conf or 0.5), 3),
        "improved_prompt": improved,
        "intent": intent,
        "variations": variations,
        "slots": slots,
        # Keep vocab_boosts empty to avoid WordNet/NLTK dependency issues
        "vocab_boosts": [],
    }


# -------------------- Refinement (sentence-style) --------------------

def _comp_phrase(comp: str | None) -> str | None:
    if not comp:
        return None
    c = comp.lower()
    if "close" in c:
        return "captured in a close-up view"
    if "wide" in c:
        return "framed wide"
    if "macro" in c:
        return "as a macro shot"
    # fallback, keep as free text
    return comp


def compose_image_prompt(kv: Dict[str, str]) -> str:
    """
    Build a natural, single-sentence image prompt from q1..q6:
    q1: subject, q2: style, q3: background, q4: composition (may include aspect),
    q5: lighting, q6: color/palette
    """
    subj  = kv.get("q1") or "subject"
    style = (kv.get("q2") or "").strip()
    bg    = (kv.get("q3") or "").strip()
    comp0 = (kv.get("q4") or "").strip()
    light = (kv.get("q5") or "").strip()
    color = (kv.get("q6") or "").strip()

    comp, ratio = _normalize_comp(comp0)
    comp_txt = _comp_phrase(comp)

    # Lead phrase
    if style:
        lead = f"Create {_article(style)} {style} image of {subj}"
    else:
        lead = f"Create an image of {subj}"

    # Optional modifiers
    mods = []
    if bg:
        mods.append(f"{_choose_prep(bg)} {bg}")
    if light:
        mods.append(f"at {light}")
    if comp_txt:
        mods.append(comp_txt)
    if ratio:
        mods.append(f"with an aspect ratio of {ratio}")
    if color:
        # prefer natural connector rather than list
        mods.append(f"using a {color} color palette")

    sentence = lead
    if mods:
        # join with commas but read like a sentence (few, natural commas)
        sentence += " " + ", ".join(mods)
    sentence += ". The scene should be sharp and detailed. Avoid: blurry, low-res, watermarks, text, logos, distortion."

    return sentence.strip()


def refine_with_answers(text: str, intent: str, answers: List[Dict[str, str]]) -> str:
    intent = (intent or "").lower()
    kv = _answers_to_map(answers)

    if intent == "image":
        return compose_image_prompt(kv)

    if intent == "email":
        recip   = kv.get("q1")  # recipient & role
        purpose = kv.get("q2")  # inform/request/update...
        tone    = kv.get("q3")  # formal/friendly/concise
        cons    = kv.get("q4")  # constraints/deadline

        parts = []
        parts.append("Write a concise, professional email")
        if recip:
            parts.append(f"to {recip}")
        if purpose:
            # make a natural clause
            parts.append(f"that {purpose}")
        sentence = " ".join(parts).strip() + "."
        if tone:
            sentence += f" Keep the tone {tone}."
        if cons:
            sentence += f" Follow these constraints: {cons}."
        sentence += " Aim for 120–150 words."
        return sentence

    if intent == "code":
        lang   = kv.get("q1") or "your preferred language"
        task   = kv.get("q2") or text or "the specified task"
        inputs = kv.get("q3")
        outputs= kv.get("q4")
        cons   = kv.get("q5")
        env    = kv.get("q6")

        s = f"Write {lang} code to {task}."
        if inputs:
            s += f" The program should accept {inputs}."
        if outputs:
            s += f" It should produce {outputs}."
        if cons:
            s += f" Observe these constraints: {cons}."
        if env:
            s += f" Target environment: {env}."
        s += " Return only the code with clear, minimal comments."
        return s

    # general fallback (rare in your current UI)
    out = (text or "").strip()
    if kv:
        extras = "; ".join(f"{k}: {v}" for k, v in kv.items() if v)
        out += f" ({extras})."
    return out


# -------------------- Alternates (natural rewordings) --------------------

def _alt_image(kv: Dict[str, str], index: int) -> str:
    subj  = (kv.get("q1") or "the subject").strip()
    style = (kv.get("q2") or "").strip()
    bg    = (kv.get("q3") or "").strip()
    comp0 = (kv.get("q4") or "").strip()
    light = (kv.get("q5") or "").strip()
    color = (kv.get("q6") or "").strip()

    comp, ratio = _normalize_comp(comp0)
    comp_txt = _comp_phrase(comp)

    templates = [
        lambda: (
            f"Generate {_article(style)} {style} image of {subj}" if style else f"Generate an image of {subj}"
        ) + (
            f" {_choose_prep(bg)} {bg}" if bg else ""
        ) + (
            f" at {light}" if light else ""
        ) + (
            f", {comp_txt}" if comp_txt else ""
        ) + (
            f", with an aspect ratio of {ratio}" if ratio else ""
        ) + (
            f", using a {color} color palette." if color else "."
        ) + " Emphasize clarity and fine detail; avoid blur, watermarks, text, or artifacts.",
        lambda: (
            f"Create a scene featuring {subj}"
            + (f" {_choose_prep(bg)} {bg}" if bg else "")
            + (f" at {light}" if light else "")
            + (f", {comp_txt}" if comp_txt else "")
            + (f", aspect ratio {ratio}" if ratio else "")
            + (f", {style} style" if style else "")
            + (f", with {color} tones." if color else ".")
            + " Aim for high fidelity and sharp focus; exclude logos and text."
        ),
        lambda: (
            (f"Produce {_article(style)} {style} composition of {subj}" if style else f"Produce a composition of {subj}")
            + (f" {_choose_prep(bg)} {bg}" if bg else "")
            + (f" under {light}" if light else "")
            + (f", {comp_txt}" if comp_txt else "")
            + (f", AR {ratio}" if ratio else "")
            + (f", palette {color}." if color else ".")
            + " Keep details crisp; avoid noise and distortion."
        ),
    ]
    return templates[index % len(templates)]()


def _alt_email(kv: Dict[str, str], index: int, base_text: str) -> str:
    recip   = kv.get("q1")
    purpose = kv.get("q2")
    tone    = kv.get("q3")
    cons    = kv.get("q4")

    who = f" to {recip}" if recip else ""
    why = f" that {purpose}" if purpose else ""
    tone_s = f" Keep the tone {tone}." if tone else ""
    cons_s = f" Follow these constraints: {cons}." if cons else ""

    variants = [
        lambda: f"Draft a professional email{who}{why}. Keep it clear and concise.{tone_s}{cons_s}",
        lambda: f"Write a concise email{who}{why}. Maintain a professional tone.{tone_s}{cons_s}",
        lambda: f"Compose a well-structured email{who}{why}. Aim for ~120–150 words.{tone_s}{cons_s}",
    ]
    return variants[index % len(variants)]()


def _alt_code(kv: Dict[str, str], index: int, base_text: str) -> str:
    lang   = kv.get("q1") or "a suitable language"
    task   = kv.get("q2") or base_text or "the specified task"
    inputs = kv.get("q3")
    outputs= kv.get("q4")
    cons   = kv.get("q5")
    env    = kv.get("q6")

    variants = [
        lambda: " ".join(filter(None, [
            f"Implement {lang} code to {task}.",
            f"Accept {inputs}." if inputs else None,
            f"Return {outputs}." if outputs else None,
            f"Constraints: {cons}." if cons else None,
            f"Environment: {env}." if env else None,
            "Output only the code with minimal comments."
        ])),
        lambda: " ".join(filter(None, [
            f"Write a {lang} function that {task}.",
            f"Inputs: {inputs}." if inputs else None,
            f"Outputs: {outputs}." if outputs else None,
            f"Observe: {cons}." if cons else None,
            f"Target: {env}." if env else None,
            "Provide a clean, self-contained solution."
        ])),
        lambda: " ".join(filter(None, [
            f"Create a {lang} routine to {task}.",
            f"Input spec: {inputs}." if inputs else None,
            f"Output spec: {outputs}." if outputs else None,
            f"Notes: {cons}." if cons else None,
            f"Runtime: {env}." if env else None,
            "Return code only."
        ])),
    ]
    return variants[index % len(variants)]()


def _alt_general(kv: Dict[str, str], index: int, base_text: str) -> str:
    extras = "; ".join(f"{k}: {v}" for k, v in kv.items() if v)
    variants = [
        lambda: f"Provide a clear, actionable response: {base_text}" + (f" ({extras})." if extras else "."),
        lambda: f"Respond concisely to: {base_text}" + (f" ({extras})." if extras else "."),
        lambda: f"Give a step-by-step answer for: {base_text}" + (f" ({extras})." if extras else "."),
    ]
    return variants[index % len(variants)]()


def _extract_kv_from_prompt(prompt: str) -> Dict[str, str]:
    """Heuristic (image only) to pull values from an existing refined prompt."""
    kv = {}
    if not prompt:
        return kv
    m = re.search(r"\bof (?:a |an )?([^,\.]+)", prompt, flags=re.I)
    if m:
        kv["q1"] = m.group(1).strip()
    m = re.search(r"^(?:create|generate|produce)\s+(?:a|an)\s+([a-z\- ]+?)\s+image\b", prompt.strip(), flags=re.I)
    if m:
        kv["q2"] = m.group(1).strip()
    m = re.search(r"\b (in|on) ([^,\.]+)", prompt, flags=re.I)
    if m:
        kv["q3"] = m.group(2).strip()
    m = re.search(r"\b at ([^,\.]+)", prompt, flags=re.I)
    if m:
        kv["q5"] = m.group(1).strip()
    m = re.search(r"color palette:\s*([^,\.]+)", prompt, flags=re.I)
    if m:
        kv["q6"] = m.group(1).strip()
    m = re.search(r"\b(?:aspect ratio|ar)\s*(\d+:\d+)", prompt, flags=re.I)
    if m:
        kv["q4"] = m.group(1).strip()
    return kv


def alternate_prompt(
    prompt: str,
    intent: str,
    answers: List[Dict[str, str]] | Dict[str, str] | None = None,
    index: int = 0
) -> str:
    """
    Public alternate generator used by /api/alternate.
    Works for image/email/code (and general fallback).
    Produces a fresh rewording each time using the 'index' (0,1,2,...).
    """
    intent = (intent or "general").lower()
    if isinstance(answers, list):
        kv = _answers_to_map(answers)
    elif isinstance(answers, dict):
        kv = answers
    else:
        kv = {}

    if intent == "image":
        if not kv:
            kv = _extract_kv_from_prompt(prompt)
        return _alt_image(kv, index)

    if intent == "email":
        return _alt_email(kv, index, prompt)

    if intent == "code":
        return _alt_code(kv, index, prompt)

    return _alt_general(kv, index, prompt)
