import os
from flask import Flask, jsonify, render_template, request

# Import your prompt logic
# (these live in promptassist/suggestion_engine.py from our earlier steps)
from promptassist.suggestion_engine import (
    suggest,
    refine_with_answers,
    alternate_prompt,
)

app = Flask(__name__, template_folder="templates", static_folder=None)

ALLOWED_INTENTS = {"image", "email", "code"}


def _coerce_intent_to_allowed(text: str, intent: str) -> str:
    """
    Keep only image/email/code. If the classifier returns something else,
    use a tiny heuristic to map it into one of the three.
    """
    if intent in ALLOWED_INTENTS:
        return intent

    t = (text or "").lower()
    if any(k in t for k in ["image", "photo", "render", "illustration", "icon", "logo", "picture"]):
        return "image"
    if any(k in t for k in ["email", "mail", "message", "professor", "manager", "recipient"]):
        return "email"
    if any(k in t for k in ["code", "function", "script", "class", "api", "python", "javascript", "java", "c++", "c#", "golang", "typescript"]):
        return "code"
    # Default to email (safe fallback)
    return "email"


@app.route("/", methods=["GET"])
def home():
    # Serves templates/index.html
    return render_template("index.html")


@app.route("/api/suggest", methods=["POST"])
def api_suggest():
    """
    Input JSON: { "text": "...", "lang": "en" }
    Output JSON mirrors suggestion_engine.suggest(...)
    but intent is coerced to image/email/code.
    """
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    lang = (payload.get("lang") or "en").strip()

    if not text:
        return jsonify({"error": "Missing 'text'"}), 400

    try:
        data = suggest(text, lang=lang)
        # Coerce to allowed intents (image/email/code) if needed
        coerced = _coerce_intent_to_allowed(text, data.get("intent", ""))
        if coerced != data.get("intent"):
            # Re-run suggest with a tiny hint so the classifier lands correctly
            hinted = f"{coerced}: {text}"
            data = suggest(hinted, lang=lang)

        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/refine", methods=["POST"])
def api_refine():
    """
    Input JSON: { "text": "...", "lang": "en", "intent": "image|email|code", "answers": [...] }
    Output JSON: { "refined_prompt": "..." }
    """
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    lang = (payload.get("lang") or "en").strip()
    intent = (payload.get("intent") or "").strip().lower()
    answers = payload.get("answers") or []

    if not text:
        return jsonify({"error": "Missing 'text'"}), 400

    # Ensure intent is one of our three
    intent = _coerce_intent_to_allowed(text, intent)

    try:
        refined = refine_with_answers(text, intent, answers)
        return jsonify({"refined_prompt": refined, "intent": intent})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/alternate", methods=["POST"])
def api_alternate():
    """
    Input JSON:
      {
        "prompt": "<latest refined prompt>",
        "intent": "image|email|code",
        "answers": [...],   # optional; the same clarify answers you submitted
        "index": 0          # which alternate template to use (0,1,2,...)
      }
    Output JSON:
      { "alternate_prompt": "..." }
    """
    payload = request.get_json(silent=True) or {}
    prompt = (payload.get("prompt") or "").strip()
    intent = (payload.get("intent") or "").strip().lower()
    answers = payload.get("answers") or []
    index = payload.get("index", 0)

    # Ensure intent is allowed
    intent = _coerce_intent_to_allowed(prompt, intent)

    try:
        alt = alternate_prompt(prompt=prompt, intent=intent, answers=answers, index=int(index))
        if not alt:
            return jsonify({"error": "No alternate generated."}), 200
        return jsonify({"alternate_prompt": alt, "intent": intent})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({"ok": True})


if __name__ == "__main__":
    # Bind to all interfaces (Docker-friendly) on port 8080, no debug in container
    app.run(host="0.0.0.0", port=8080, debug=False)
