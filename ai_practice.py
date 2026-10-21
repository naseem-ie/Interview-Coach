"""Streamlit screen for AI practice: questions written by the local AI for uncovered skill gaps."""

import random
import time

import streamlit as st

from coach import CoachError
from progress import (
    XP_PER_CORRECT, ai_questions, ai_skill_stats, question_history, record_answer, report_ai_question,
    save_ai_questions,
)
from question_writer import write_questions
from quiz import _priority

LETTERS = "ABCD"
PER_SKILL = 5
ROUND_SIZE = 5


def _generate(conn, today, job, skills):
    """Ask the AI for questions, one skill at a time, saving as we go."""
    with st.status("✨ Your local AI is writing questions...", expanded=True) as status:
        total = 0
        for number, skill in enumerate(skills, start=1):
            st.write(f"{number} of {len(skills)}: **{skill}** (about 1 to 2 minutes)")
            start = time.time()
            try:
                questions = write_questions(skill, job["role"], count=PER_SKILL)
            except CoachError as error:
                status.update(label="Could not finish", state="error")
                return f"❌ {error}" + (f" ({total} questions were saved first.)" if total else "")
            added = save_ai_questions(conn, today, job["id"], skill, questions)
            total += added
            st.write(f"✅ {added} questions saved in {time.time() - start:.0f} s")
        status.update(label=f"Done: {total} new questions saved", state="complete", expanded=False)
    return f"✨ {total} new questions saved. Answer them below."


def _setup(conn, today, job, gaps, pool):
    """Show which skill gaps have questions and let you write more."""
    counts = {}
    for q in pool:
        counts[q["skill"].lower()] = counts.get(q["skill"].lower(), 0) + 1

    with st.expander("✨ Add AI questions for your skill gaps", expanded=not pool):
        if gaps:
            st.write("These skill gaps from Notion are **not covered by the question bank**:")
            for gap in gaps:
                count = counts.get(gap.lower(), 0)
                st.write(f"{'✅' if count else '⬜'} {gap}: {count or 'no'} questions")
        else:
            st.write("The question bank covers every skill gap for this job. You can still add any topic below.")

        missing = [gap for gap in gaps if not counts.get(gap.lower())]
        chosen = st.multiselect("Skills the AI should write questions about", gaps, default=missing[:1])
        extra = st.text_input("Or type any other topic", placeholder="e.g. SAP Ariba, PowerShell, Agile")
        if extra.strip():
            chosen = chosen + [extra.strip()]
        st.caption(
            f"{PER_SKILL} questions per skill, written on your laptop by the free local AI. "
            "It takes about 1 to 2 minutes per skill, so start with one or two."
        )
        if st.button("✨ Let the AI write questions", type="primary", disabled=not chosen):
            st.session_state["ai_message"] = _generate(conn, today, job, chosen)
            st.session_state.pop("ai", None)
            st.rerun()


def _new_round(pool, history):
    """Up to 5 questions: wrong last time first, then new, then seen, then mastered."""
    ordered = list(pool)
    random.shuffle(ordered)
    ordered.sort(key=lambda q: _priority(q, history))
    return [q["id"] for q in ordered[:ROUND_SIZE]]


def _round_results(conn, pool, state):
    """End of a round: score, what to revisit, and how each skill is going."""
    by_id = {q["id"]: q for q in pool}
    results = state["results"]
    right = sum(results.values())
    st.subheader(f"🏁 Round complete: {right} of {len(results)} right")
    missed = [by_id[i] for i, ok in results.items() if not ok and i in by_id]
    if missed:
        st.markdown("**Coming back first next round:**")
        for q in missed:
            st.markdown(f"- {q['question']}")
    st.markdown("**Your AI practice skills**")
    for skill, s in ai_skill_stats(conn, pool).items():
        icon = {"Mastered": "✅", "Learning": "📘", "Not started": "⬜"}[s["status"]]
        st.write(f"{icon} {skill}: {s['correct']} of {s['total']} right · {s['status']}")
    if all(s["status"] == "Mastered" for s in ai_skill_stats(conn, pool).values()):
        st.success("Every AI skill is mastered. Write questions for another skill above to keep going.")
    if st.button("▶️ Another round", type="primary"):
        st.session_state.pop("ai")
        st.rerun()


def render_ai_practice(conn, today, job, gaps):
    """AI practice for one job: write questions, then answer them in rounds of 5."""
    challenge_id = f"{job['id']}:ai"
    pool = ai_questions(conn, gaps, job["id"])
    message = st.session_state.pop("ai_message", None)
    if message:
        (st.error if message.startswith("❌") else st.success)(message)
    _setup(conn, today, job, gaps, pool)
    if not pool:
        st.info("No AI questions yet. Pick a skill above and click ✨ Let the AI write questions.")
        return

    ids = {q["id"] for q in pool}
    state = st.session_state.get("ai")
    if state is None or state["job"] != job["id"]:
        state = st.session_state["ai"] = {
            "job": job["id"], "round": _new_round(pool, question_history(conn)),
            "index": 0, "results": {}, "feedback": None,
        }
    state["round"] = [i for i in state["round"] if i in ids]  # drop removed questions
    if state["index"] >= len(state["round"]):
        _round_results(conn, pool, state)
        return
    question = next(q for q in pool if q["id"] == state["round"][state["index"]])

    st.caption(f"🤖 {len(pool)} AI practice questions for this job, practised {ROUND_SIZE} at a time")
    st.progress(state["index"] / len(state["round"]), text=f"Question {state['index'] + 1} of {len(state['round'])}")
    with st.container(border=True):
        st.caption(f"🤖 AI practice · {question['skill']}")
        if state["feedback"] is None:
            with st.form(f"ai-{question['id']}"):
                st.markdown(f"**{question['question']}**")
                choice = st.radio(
                    "Your answer",
                    options=range(len(question["options"])),
                    format_func=lambda i: f"{LETTERS[i]}) {question['options'][i]}",
                    index=None,
                )
                submitted = st.form_submit_button("Submit answer", type="primary")
            if submitted and choice is None:
                st.warning("Pick an answer first.")
            elif submitted:
                correct = choice == question["answer"]
                record_answer(conn, today, challenge_id, question, correct)
                state["results"][question["id"]] = correct
                state["feedback"] = {"correct": correct, "chosen": LETTERS[choice]}
                st.rerun()
        else:
            st.markdown(f"**{question['question']}**")
            if state["feedback"]["correct"]:
                st.success(f"✅ Correct! +{XP_PER_CORRECT} XP")
            else:
                st.error(
                    f"❌ You chose {state['feedback']['chosen']}; the answer is {LETTERS[question['answer']]}."
                )
            st.info(f"**Answer:** {question['options'][question['answer']]}\n\n{question['explanation']}")
            st.caption(
                "🤖 Written by AI, not checked by a person. If the question or answer looks wrong, "
                "remove it and it won't be shown again."
            )
            last = state["index"] + 1 >= len(state["round"])
            col1, col2 = st.columns(2)
            if col1.button("See round results 🏁" if last else "Next question ➡️", type="primary"):
                state["index"] += 1
                state["feedback"] = None
                st.rerun()
            if col2.button("👎 This is wrong, remove it"):
                report_ai_question(conn, question["id"])
                state["results"].pop(question["id"], None)
                state["round"].remove(question["id"])
                state["feedback"] = None
                st.toast("Removed. Thanks for checking!")
                st.rerun()
