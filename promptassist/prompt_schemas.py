SCHEMAS = {
    "general": {
        "required": ["tone", "length", "format"],
        "template": (
            "Role: Helpful assistant.\n"
            "Goal: {goal}.\n"
            "Inputs: {inputs}.\n"
            "Constraints: {length}, {tone}.\n"
            "Output: {format}.\n"
        )
    }
}

def build_prompt_from_slots(intent, slots, schema):
    values = {
        "goal": slots.get("goal", "Complete the user’s request."),
        "inputs": slots.get("inputs", ""),
        "length": slots.get("length", "120–150 words"),
        "tone": slots.get("tone", "professional"),
        "format": slots.get("format", "plain text only")
    }
    return schema["template"].format(**values)
