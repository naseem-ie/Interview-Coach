"""AI question writer: asks the local Ollama model for multiple-choice practice questions.

Used for skill gaps the reviewed question bank does not cover. The AI writes the correct
answer and three wrong ones separately; this code shuffles them and checks the result, so a
badly formed question is dropped rather than shown.
"""

import hashlib
import json
import random

import httpx
import ollama

from coach import CoachError, model_name

AI_TOPIC = "ai"

QUESTIONS_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "correct_answer": {"type": "string"},
                    "wrong_answers": {"type": "array", "items": {"type": "string"}},
                    "explanation": {"type": "string"},
                },
                "required": ["question", "correct_answer", "wrong_answers", "explanation"],
            },
        }
    },
    "required": ["questions"],
}


def build_messages(skill, role, count):
    """The instructions we send to the AI."""
    system = (
        "You write multiple-choice practice questions that help a candidate prepare for a job "
        "interview. Each question has exactly one correct answer and exactly three wrong answers "
        "that sound plausible but are clearly wrong to an expert. Keep every answer under 15 words. "
        "Add a one or two sentence explanation of why the correct answer is right. Only use facts "
        "you are sure of. Do not write 'all of the above' or 'none of the above'. Reply in JSON only."
    )
    user = (
        f"Role: {role}\nTopic: {skill}\n\n"
        f"Write {count} different questions about this topic that an interviewer for this role "
        "might check, from basic to practical."
    )
    return [{"role": "system", "content": system}, {"role": "user", "content": user}]


def _clean(text):
    return " ".join(str(text).split())


def question_id(skill, question):
    """A stable id, so the same question is never saved twice."""
    digest = hashlib.sha1(f"{skill.lower()}|{question.lower()}".encode()).hexdigest()[:12]
    return f"ai-{digest}"


def parse_questions(text, skill, rng=None):
    """Turn the AI's JSON reply into questions in the bank's format. Bad ones are dropped."""
    rng = rng or random.Random()
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise CoachError("The AI's reply was not valid JSON. Try again.") from error

    items = data.get("questions", []) if isinstance(data, dict) else []
    questions, seen = [], set()
    for item in items:
        if not isinstance(item, dict):
            continue
        question = _clean(item.get("question", ""))
        correct = _clean(item.get("correct_answer", ""))
        explanation = _clean(item.get("explanation", ""))
        wrong = []
        for answer in item.get("wrong_answers", []):
            answer = _clean(answer)
            if answer and answer.lower() != correct.lower() and answer.lower() not in [w.lower() for w in wrong]:
                wrong.append(answer)
        if not question or not correct or len(wrong) < 3 or question.lower() in seen:
            continue
        seen.add(question.lower())
        options = [correct] + wrong[:3]
        rng.shuffle(options)
        questions.append({
            "id": question_id(skill, question),
            "topic": AI_TOPIC,
            "skill": skill,
            "question": question,
            "options": options,
            "answer": options.index(correct),
            "explanation": explanation or "No explanation given.",
        })
    return questions


def write_questions(skill, role, count=5, client=None):
    """Ask the AI for practice questions on one skill. Returns a list (may be shorter than count)."""
    client = client or ollama.Client()
    try:
        response = client.chat(
            model=model_name(),
            messages=build_messages(skill, role, count),
            format=QUESTIONS_SCHEMA,
            think=False,
            options={"temperature": 0.3},
        )
    except (ConnectionError, httpx.HTTPError) as error:
        raise CoachError(
            "Could not reach Ollama. Check the llama icon is in the system tray, "
            "or run 'ollama serve' in a terminal."
        ) from error
    except ollama.ResponseError as error:
        raise CoachError(f"Ollama returned an error: {error}") from error
    return parse_questions(response.message.content, skill)[:count]
