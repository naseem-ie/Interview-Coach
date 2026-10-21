"""AI coach: scores interview answers with a local Ollama model (free, private, offline)."""

import json
import os

import httpx
import ollama
from dotenv import load_dotenv

DEFAULT_MODEL = "qwen3.5:4b"
POINTS_PER_ITEM = 2

# What a strong answer should do. The AI only says yes or no to each item;
# the score is worked out by this code, so the same answer always gets the same score.
CHECKLIST = {
    "situation": "Sets the scene: what happened and why it mattered",
    "action": "Explains the specific steps the candidate personally took",
    "result": "Gives a clear outcome, ideally measurable (time, %, users, SLA)",
    "ownership": "Shows ownership and judgement, using 'I' for their own actions",
    "relevance": "Answers the question asked and fits the role",
}

FEEDBACK_SCHEMA = {
    "type": "object",
    "properties": {
        "checklist": {
            "type": "object",
            "properties": {item: {"type": "boolean"} for item in CHECKLIST},
            "required": list(CHECKLIST),
        },
        "strength": {"type": "string"},
        "tips": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["checklist", "strength", "tips"],
}


class CoachError(Exception):
    """Something went wrong talking to the AI model."""


def model_name():
    """The Ollama model to use. Set OLLAMA_MODEL in .env to try a different one."""
    load_dotenv()
    return os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)


def build_messages(question, answer, role):
    """The instructions and the answer we send to the AI."""
    checklist_lines = "\n".join(f"- {item}: {meaning}" for item, meaning in CHECKLIST.items())
    system = (
        f"You are a fair but demanding interviewer hiring for a {role} role. "
        "Judge the candidate's answer against each checklist item. Mark an item true only if "
        "the answer clearly does it. Then give one specific strength and exactly two short, "
        "specific tips to improve this answer. Reply in JSON only."
    )
    user = (
        f"Question: {question}\n\nCandidate's answer: {answer}\n\n"
        f"Checklist:\n{checklist_lines}"
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def parse_feedback(text):
    """Turn the AI's JSON reply into a feedback dictionary with a score out of 10."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise CoachError("The AI's reply was not valid JSON. Try again.") from error

    raw = data.get("checklist", {}) if isinstance(data, dict) else {}
    checklist = {item: bool(raw.get(item, False)) for item in CHECKLIST}
    tips = [str(tip) for tip in data.get("tips", []) if str(tip).strip()][:2]
    return {
        "score": POINTS_PER_ITEM * sum(checklist.values()),
        "checklist": checklist,
        "strength": str(data.get("strength", "")).strip(),
        "tips": tips,
    }


def score_answer(question, answer, role, client=None):
    """Ask the AI to judge an answer. Returns score (0-10), checklist, strength and tips."""
    if not answer or not answer.strip():
        raise ValueError("Write an answer first.")
    client = client or ollama.Client()
    try:
        response = client.chat(
            model=model_name(),
            messages=build_messages(question, answer, role),
            format=FEEDBACK_SCHEMA,
            think=False,
            options={"temperature": 0},
        )
    except (ConnectionError, httpx.HTTPError) as error:
        raise CoachError(
            "Could not reach Ollama. Check the llama icon is in the system tray, "
            "or run 'ollama serve' in a terminal."
        ) from error
    except ollama.ResponseError as error:
        raise CoachError(f"Ollama returned an error: {error}") from error
    return parse_feedback(response.message.content)
