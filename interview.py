"""Mock interview questions: classic behavioural questions plus questions built from the job."""

import random

from quiz import skill_gap_items

QUESTIONS_PER_INTERVIEW = 5
JOB_QUESTIONS = 2
PASS_SCORE = 6  # out of 10: counts as a "correct" answer for XP

BEHAVIOURAL = [
    "Tell me about a time you resolved a major incident under pressure.",
    "Tell me about a time you dealt with a difficult customer or stakeholder.",
    "Tell me about a time you made a mistake at work. What did you learn?",
    "Tell me about a process you improved. What was the result?",
    "Tell me about a time you had to learn a new tool or technology quickly.",
    "Tell me about a time you disagreed with a colleague or manager. How did you handle it?",
    "Tell me about a time you had several urgent tasks at once. How did you prioritise?",
    "Tell me about a time you explained a technical problem to a non-technical person.",
    "Tell me about a time you went beyond your role to help a customer or your team.",
    "Tell me about a time you found the root cause of a recurring problem.",
    "Tell me about a time you missed a deadline or SLA. What happened next?",
    "Tell me about a time you worked with a team in another country or time zone.",
    "Tell me about a time you received critical feedback. What did you do with it?",
    "Tell me about a time you used data to make a decision or prove a point.",
    "Tell me about a time you documented something that helped others work faster.",
]

SKILL_TEMPLATES = [
    "This role needs {skill}. Tell me about a time you used it, or something close to it. "
    "What did you do and what was the result?",
    "How would you get up to speed on {skill} in your first month here? "
    "Give an example of a time you learned something similar.",
]

ROLE_QUESTIONS = [
    "Why are you a good fit for this {role} role? Give a specific example from your experience.",
    "What would you focus on in your first 90 days as a {role}, and why?",
]


def build_interview(job, rng):
    """Five questions: two about this job (from its skill gaps or role) and three behavioural."""
    skills = skill_gap_items(job.get("skill_gaps"))
    rng.shuffle(skills)
    role = job.get("role") or "support"
    job_questions = [
        rng.choice(SKILL_TEMPLATES).format(skill=skill) for skill in skills[:JOB_QUESTIONS]
    ]
    for template in ROLE_QUESTIONS:
        if len(job_questions) < JOB_QUESTIONS:
            job_questions.append(template.format(role=role))
    behavioural = rng.sample(BEHAVIOURAL, QUESTIONS_PER_INTERVIEW - len(job_questions))
    # Start with an easier behavioural question, like a real interview
    return behavioural[:1] + job_questions + behavioural[1:]


def summarise(results):
    """results is a list of {question, score}. Average, best and weakest of the answered ones."""
    scored = [r for r in results if r.get("score") is not None]
    if not scored:
        return {"answered": 0, "average": 0, "best": None, "weakest": None}
    best = max(scored, key=lambda r: r["score"])
    weakest = min(scored, key=lambda r: r["score"])
    if best["score"] == weakest["score"]:
        best = weakest = None  # all the same score: no strongest or weakest to point at
    return {
        "answered": len(scored),
        "average": round(sum(r["score"] for r in scored) / len(scored), 1),
        "best": best,
        "weakest": weakest,
    }
