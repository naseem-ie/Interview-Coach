"""Try the AI coach in the terminal: answer one question and get scored feedback."""

import random
import time

from coach import CHECKLIST, CoachError, score_answer

ROLE = "Application Support Engineer"
QUESTIONS = [
    "Tell me about a time you resolved a major incident.",
    "Tell me about a time you dealt with a difficult customer or stakeholder.",
    "Tell me about a time you made a mistake at work and what you learned.",
    "Tell me about a process you improved and the result.",
]

question = random.choice(QUESTIONS)
print(f"\nInterview question:\n  {question}\n")
answer = input("Type your answer on one line, then press Enter:\n> ")

print("\nThe coach is reading your answer (usually under a minute)...")
start = time.time()
try:
    feedback = score_answer(question, answer, ROLE)
except (CoachError, ValueError) as error:
    raise SystemExit(f"\n{error}")

print(f"\nScore: {feedback['score']}/10  (took {time.time() - start:.0f}s)\n")
for item, met in feedback["checklist"].items():
    print(f"  {'✓' if met else '✗'} {CHECKLIST[item]}")
print(f"\nStrength: {feedback['strength']}")
for number, tip in enumerate(feedback["tips"], start=1):
    print(f"Tip {number}: {tip}")
