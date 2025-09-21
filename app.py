import os
from flask import Flask, jsonify, render_template, request

# ---- Your prompt logic (unchanged) ----
from promptassist.suggestion_engine import (
    suggest,
    refine_with_answers,
    alternate_prompt,
)

app = Flask(__name__, template_folder="templates", static_folder=None)

ALLOWED_INTENTS = {"image", "email", "code"}

def _coerce_intent_to_allowed(text: str, intent: str) -> str:
    if intent in ALLOWED_INTENTS:
        return intent
    t = (text or "").lower()
    if any(k in t for k in ["image","photo","render","illustration","icon","logo","picture"]):
        return "image"
    if any(k in t for k in ["email","mail","message","professor","manager","recipient"]):
        return "email"
    if any(k in t for k in ["code","function","script","class","api","python","javascript","java","c++","c#","golang","typescript"]):
        return "code"
    return "email"

@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

@app.route("/api/suggest", methods=["POST"])
def api_suggest():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    lang = (payload.get("lang") or "en").strip()
    intent = (payload.get("intent") or "").strip().lower()

    if not text and not intent:
        return jsonify({"error": "Missing 'intent' or 'text'"}), 400

    try:
        if intent in ALLOWED_INTENTS:
            data = suggest(text or "", lang=lang)
            data["intent"] = intent
        else:
            data = suggest(text, lang=lang)
            coerced = _coerce_intent_to_allowed(text, data.get("intent", ""))
            if coerced != data.get("intent"):
                hinted = f"{coerced}: {text}"
                data = suggest(hinted, lang=lang)
                data["intent"] = coerced
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/refine", methods=["POST"])
def api_refine():
    payload = request.get_json(silent=True) or {}
    text = (payload.get("text") or "").strip()
    lang = (payload.get("lang") or "en").strip()
    intent = (payload.get("intent") or "").strip().lower()
    answers = payload.get("answers") or []

    if not intent and not text:
        return jsonify({"error": "Missing 'intent' or 'text'"}), 400

    intent = _coerce_intent_to_allowed(text, intent)

    try:
        refined = refine_with_answers(text, intent, answers)
        return jsonify({"refined_prompt": refined, "intent": intent})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/alternate", methods=["POST"])
def api_alternate():
    payload = request.get_json(silent=True) or {}
    prompt = (payload.get("prompt") or "").strip()
    intent = (payload.get("intent") or "").strip().lower()
    answers = payload.get("answers") or []
    index = payload.get("index", 0)

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
    # Bind to Render's $PORT if present; default to 8080 locally
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
