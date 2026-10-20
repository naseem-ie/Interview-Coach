"""Try the question bank in the terminal: python try_quiz.py [topic] [number]"""

import json
import random
import sys
from pathlib import Path

bank = json.loads((Path(__file__).parent / "data" / "questions.json").read_text(encoding="utf-8"))
topic = sys.argv[1] if len(sys.argv) > 1 else "all"
count = int(sys.argv[2]) if len(sys.argv) > 2 else 5

if topic != "all" and topic not in bank["topics"]:
    raise SystemExit(f"Unknown topic. Choose from: all, {', '.join(bank['topics'])}")

pool = [q for q in bank["questions"] if topic == "all" or q["topic"] == topic]
questions = random.sample(pool, min(count, len(pool)))
score = 0

for number, q in enumerate(questions, start=1):
    print(f"\nQuestion {number} of {len(questions)}  [{bank['topics'][q['topic']]['name']}]")
    print(q["question"])
    for letter, option in zip("ABCD", q["options"]):
        print(f"  {letter}) {option}")
    choice = input("Your answer (A/B/C/D): ").strip().upper()
    correct = "ABCD"[q["answer"]]
    if choice == correct:
        score += 1
        print("Correct!")
    else:
        print(f"Not quite. The answer is {correct}.")
    print(f"Why: {q['explanation']}")
    print(f"Study: {bank['topics'][q['topic']]['study_link']}")

print(f"\nYou scored {score} out of {len(questions)}.")