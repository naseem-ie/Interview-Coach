"""Streamlit screen for the mock interview: open questions, typed answers, AI feedback."""

import hashlib
import random

import streamlit as st

from coach import CHECKLIST, CoachError, score_answer
from interview import PASS_SCORE, QUESTIONS_PER_INTERVIEW, build_interview, summarise
from progress import complete_challenge, interviews, record_answer, save_interview

MIN_WORDS = 15


def _question_record(question):
    """The answers table needs an id and topic for XP and streaks."""
    digest = hashlib.sha1(question.encode()).hexdigest()[:10]
    return {"id": f"interview-{digest}", "topic": "interview"}


def _show_feedback(result):
    """Score, checklist, strength and tips for one answer."""
    feedback = result["feedback"]
    score = result["score"]
    colour = "🟢" if score >= 8 else "🟡" if score >= PASS_SCORE else "🔴"
    st.markdown(f"### {colour} {score}/10")
    for item, met in feedback["checklist"].items():
        st.write(f"{'✅' if met else '❌'} **{item.capitalize()}**: {CHECKLIST[item]}")
    if feedback["strength"]:
        st.success(f"💪 **Strength:** {feedback['strength']}")
    if feedback["tips"]:
        st.info("**How to improve:**\n" + "\n".join(f"- {tip}" for tip in feedback["tips"]))


def _history(conn, job):
    """Past interviews for this job, with every answer to read again."""
    past = interviews(conn, job["id"])
    if not past:
        return
    averages = [p["average"] for p in past]
    st.markdown("**Your past interviews for this job**")
    st.caption(
        f"Interviews: {len(past)} · Last: {averages[0]}/10 · Best: {max(averages)}/10"
    )
    for number, interview in enumerate(past[:5]):
        with st.expander(f"{interview['day']}: {interview['average']}/10 ({interview['answered']} answers)"):
            for answer in interview["answers"]:
                st.markdown(f"**{answer['question']}**")
                st.write(f"_{answer['answer']}_")
                st.caption(
                    f"{answer['score']}/10 · Tips: " + " ".join(answer["feedback"].get("tips", []))
                )


def _start_screen(conn, job):
    st.write(
        f"A {QUESTIONS_PER_INTERVIEW}-question practice interview for **{job['role']}**: "
        "behavioural questions plus questions about this job's skill gaps. Type your answer the way "
        "you would say it. The AI scores each answer out of 10 and tells you how to improve it."
    )
    with st.expander("💡 How answers are scored (2 points each)"):
        for item, meaning in CHECKLIST.items():
            st.write(f"**{item.capitalize()}**: {meaning}")
        st.caption(
            "This is the STAR method: Situation, Task, Action, Result. Aim for 6 to 10 sentences, "
            "say 'I' for what you did, and end with a number if you can (time saved, SLA, users)."
        )
    st.caption("Each answer takes about a minute to score on your laptop. A full interview takes about 15 minutes.")
    if st.button("🎤 Start the interview", type="primary"):
        st.session_state["interview"] = {
            "job": job["id"],
            "questions": build_interview(job, random.Random()),
            "index": 0,
            "results": [],
            "saved": False,
        }
        st.rerun()
    _history(conn, job)


def _finish(conn, today, job, state):
    results = state["results"]
    summary = summarise(results)
    if not state["saved"] and summary["answered"]:
        save_interview(conn, today, job["id"], results, summary["average"])
        if summary["answered"] >= 3:
            complete_challenge(conn, today, f"{job['id']}:interview")
        state["saved"] = True

    st.subheader("🏁 Interview complete")
    if not summary["answered"]:
        st.info("You skipped every question, so nothing was saved.")
    else:
        st.metric("Average score", f"{summary['average']}/10", help=f"{summary['answered']} answers scored")
        if summary["best"]:
            st.write(f"💪 **Strongest:** {summary['best']['question']} ({summary['best']['score']}/10)")
            st.write(f"🎯 **Work on:** {summary['weakest']['question']} ({summary['weakest']['score']}/10)")
        else:
            st.write(
                f"Every answer scored {summary['average']:g}/10. Open each one below to see which "
                "checklist items were missing and the tips to improve."
            )
        for result in results:
            if result.get("score") is None:
                continue
            with st.expander(f"{result['score']}/10 · {result['question']}"):
                st.write(f"_{result['answer']}_")
                _show_feedback(result)
        st.caption(
            f"Answers scoring {PASS_SCORE}/10 or more earn XP. Finishing at least 3 answers keeps your streak going."
        )
    if st.button("🎤 Start another interview", type="primary"):
        st.session_state.pop("interview")
        st.rerun()


def render_interview(conn, today, job):
    """Mock interview: start screen, one question at a time with feedback, then a summary."""
    state = st.session_state.get("interview")
    if state is None or state["job"] != job["id"]:
        _start_screen(conn, job)
        return

    questions = state["questions"]
    if state["index"] >= len(questions):
        _finish(conn, today, job, state)
        return

    question = questions[state["index"]]
    st.progress(state["index"] / len(questions), text=f"Question {state['index'] + 1} of {len(questions)}")
    with st.container(border=True):
        st.markdown(f"#### 🎤 {question}")
        answered = len(state["results"]) > state["index"]
        if not answered:
            with st.form(f"interview-{state['index']}"):
                answer = st.text_area(
                    "Your answer", height=220,
                    placeholder="Situation: ... I ... The result was ...",
                )
                submitted = st.form_submit_button("Submit for feedback", type="primary")
            if submitted:
                words = len(answer.split())
                if words < MIN_WORDS:
                    st.warning(f"That's {words} words. Write at least {MIN_WORDS} so the coach has something to judge.")
                else:
                    with st.spinner("The coach is reading your answer (about a minute)..."):
                        try:
                            feedback = score_answer(question, answer, job["role"])
                        except CoachError as error:
                            st.error(f"{error} Your answer is still in the box; click Submit to try again.")
                            feedback = None
                    if feedback:
                        record_answer(
                            conn, today, f"{job['id']}:interview", _question_record(question),
                            feedback["score"] >= PASS_SCORE,
                        )
                        state["results"].append({
                            "question": question, "answer": answer,
                            "score": feedback["score"], "feedback": feedback,
                        })
                        st.rerun()
            if st.button("Skip this question ⏭️"):
                state["results"].append({"question": question, "answer": "", "score": None, "feedback": None})
                state["index"] += 1
                st.rerun()
        else:
            result = state["results"][state["index"]]
            with st.expander("Your answer"):
                st.write(result["answer"])
            _show_feedback(result)
            last = state["index"] + 1 >= len(questions)
            if st.button("See interview summary 🏁" if last else "Next question ➡️", type="primary"):
                state["index"] += 1
                st.rerun()
    if st.button("End interview now"):
        while len(state["results"]) < len(questions):
            state["results"].append({"question": questions[len(state["results"])], "answer": "", "score": None, "feedback": None})
        state["index"] = len(questions)
        st.rerun()
