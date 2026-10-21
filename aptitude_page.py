"""Streamlit screens for extra aptitude practice and timed mock tests."""

import random
import time

import streamlit as st

from aptitude import (
    EXTRA_ID, MOCK_FORMATS, MOCK_ID, TARGET_SECONDS, build_mock, extra_question, score_mock,
)
from aptitude_tips import GUIDE, TIPS, tip_for
from progress import mock_tests, record_answer, record_mock_test

LETTERS = "ABCD"


def _answer_form(question, key):
    """Show a question with A-D options. Returns the chosen index, or None if not submitted."""
    with st.form(key):
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
        return None
    return choice if submitted else None


def show_tip(question):
    """Show the quick trick for this type of question, if there is one."""
    tip = tip_for(question)
    if tip:
        st.success(f"💡 **Trick: {tip['title']}.** {tip['trick']}\n\n_Example: {tip['example']}_")


# ---------- Tips and tricks ----------

def render_tips(bank):
    """A study guide: test strategy, shortcuts and one trick per question type."""
    st.write(
        "Read this once now, then come back before a test. After every practice question "
        "you'll also see the trick for that type of question."
    )
    for title, body in GUIDE:
        with st.expander(title):
            st.markdown(body)
    with st.expander("💡 Every question type with an example"):
        for tip in TIPS.values():
            st.markdown(f"**{tip['title']}:** {tip['trick']}  \n_Example: {tip['example']}_")
    links = " · ".join(
        f"[{bank['topics'][t]['name']}]({bank['topics'][t]['study_link']})"
        for t in ["numerical", "logical", "verbal"]
    )
    st.caption(f"📚 More free practice: {links}")


# ---------- Practise more ----------

def render_extra(bank, conn, today):
    """Unlimited extra questions with instant feedback."""
    state = st.session_state.setdefault("extra", {"right": 0, "done": 0})
    if "question" not in state:
        state["question"] = extra_question(bank, random.Random())
        state["started"] = time.time()
        state["feedback"] = None
    question = state["question"]

    st.caption(f"This session: {state['right']} of {state['done']} right. Keep going as long as you like.")
    with st.container(border=True):
        st.caption(bank["topics"][question["topic"]]["name"])
        if state["feedback"] is None:
            choice = _answer_form(question, f"extra-{question['id']}")
            if choice is not None:
                correct = choice == question["answer"]
                record_answer(conn, today, EXTRA_ID, question, correct)
                state["done"] += 1
                state["right"] += int(correct)
                state["feedback"] = {
                    "correct": correct,
                    "chosen": LETTERS[choice],
                    "seconds": round(time.time() - state["started"]),
                }
                st.rerun()
        else:
            feedback = state["feedback"]
            st.markdown(f"**{question['question']}**")
            if feedback["correct"]:
                st.success("✅ Correct!")
            else:
                st.error(f"❌ You chose {feedback['chosen']}; the answer is {LETTERS[question['answer']]}.")
            pace = "✅ on pace" if feedback["seconds"] <= TARGET_SECONDS else "⚠️ slower than test pace"
            st.caption(f"⏱️ {feedback['seconds']} s · {pace}")
            st.info(f"**Answer:** {question['options'][question['answer']]}\n\n{question['explanation']}")
            show_tip(question)
            if st.button("Next question ➡️", type="primary"):
                state.pop("question")
                st.rerun()


# ---------- Timed mock test ----------

@st.fragment(run_every=1)
def _countdown(deadline, limit):
    """Live clock that refreshes every second and ends the test when time is up."""
    left = deadline - time.time()
    if left <= 0:
        st.rerun(scope="app")
    minutes, seconds = divmod(int(left), 60)
    st.progress(max(left, 0) / limit, text=f"⏱️ {minutes}:{seconds:02d} left")


def _start_screen(conn):
    """Pick a format and start."""
    format_key = st.selectbox(
        "Choose a test", list(MOCK_FORMATS), format_func=lambda k: MOCK_FORMATS[k]["name"]
    )
    fmt = MOCK_FORMATS[format_key]
    total = sum(fmt["mix"].values())
    st.write(f"**{total} questions in {fmt['minutes']} minutes.** {fmt['about']}")
    st.caption(
        "No feedback until the end, like the real thing. You can skip a question, but you cannot "
        "go back. The test ends when the clock runs out."
    )
    history = mock_tests(conn, format_key)
    if history:
        best = max(history, key=lambda r: r["right"])
        last = history[0]
        st.caption(
            f"Your last result: {last['right']}/{last['total']} on {last['day']} · "
            f"Best: {best['right']}/{best['total']} · Tests taken: {len(history)}"
        )
    if st.button("▶️ Start the test", type="primary"):
        rng = random.Random()
        questions = build_mock(st.session_state["bank_for_mock"], format_key, rng)
        limit = fmt["minutes"] * 60
        st.session_state["mock"] = {
            "format": format_key,
            "questions": questions,
            "index": 0,
            "chosen": {},
            "start": time.time(),
            "deadline": time.time() + limit,
            "limit": limit,
            "saved": False,
        }
        st.rerun()


def _results(conn, today, bank, state):
    """Score, save once, and show what to work on."""
    questions = state["questions"]
    result = score_mock(questions, state["chosen"])
    used = max(0, round(min(time.time(), state["deadline"]) - state["start"]))
    if not state["saved"]:
        record_mock_test(
            conn, today, state["format"], result["right"], result["answered"], result["total"], used
        )
        state["saved"] = True
        state["used"] = used
    used = state["used"]

    st.subheader("🏁 Test finished")
    percent = round(100 * result["right"] / result["total"])
    st.write(
        f"You got **{result['right']} of {result['total']}** right ({percent}%), answered "
        f"**{result['answered']}**, in {used // 60} min {used % 60} s."
    )
    if result["answered"]:
        st.caption(f"Average {used / result['answered']:.0f} seconds per answered question.")
    if result["answered"] < result["total"]:
        st.caption(
            f"{result['total'] - result['answered']} not answered. Unfinished tests are normal in "
            "speed tests; aim to answer a few more each time."
        )

    st.markdown("**By type**")
    for topic, counts in result["by_topic"].items():
        share = counts["right"] / counts["total"]
        st.progress(share, text=f"{bank['topics'][topic]['name']}: {counts['right']}/{counts['total']}")

    weakest = min(result["by_topic"], key=lambda t: result["by_topic"][t]["right"] / result["by_topic"][t]["total"])
    if len(result["by_topic"]) > 1:
        st.caption(
            f"💡 Your weakest area this time: **{bank['topics'][weakest]['name']}**. "
            "See 📘 Tips & tricks above for shortcuts."
        )

    with st.expander("Review every question"):
        for number, q in enumerate(questions, start=1):
            chosen = state["chosen"].get(q["id"])
            if chosen is None:
                mark = "⬜ skipped or not reached"
            elif chosen == q["answer"]:
                mark = "✅"
            else:
                mark = f"❌ you chose {LETTERS[chosen]}"
            st.markdown(
                f"**{number}. {q['question']}**  \n{mark} · answer {LETTERS[q['answer']]}) "
                f"{q['options'][q['answer']]}  \n_{q['explanation']}_"
            )
            tip = tip_for(q)
            if tip:
                st.caption(f"💡 {tip['title']}: {tip['trick']}")

    if st.button("Take another test", type="primary"):
        st.session_state.pop("mock")
        st.rerun()


def render_mock(bank, conn, today):
    """Timed mock test: start screen, the test itself, then results."""
    st.session_state["bank_for_mock"] = bank
    state = st.session_state.get("mock")
    if state is None:
        _start_screen(conn)
        return

    questions = state["questions"]
    finished = state["index"] >= len(questions) or time.time() >= state["deadline"]
    if finished:
        _results(conn, today, bank, state)
        return

    st.markdown(f"**{MOCK_FORMATS[state['format']]['name']}**")
    _countdown(state["deadline"], state["limit"])
    question = questions[state["index"]]
    st.caption(f"Question {state['index'] + 1} of {len(questions)} · {bank['topics'][question['topic']]['name']}")
    choice = _answer_form(question, f"mock-{state['index']}-{question['id']}")
    if choice is not None and time.time() < state["deadline"]:
        state["chosen"][question["id"]] = choice
        record_answer(conn, today, MOCK_ID, question, choice == question["answer"])
        state["index"] += 1
        st.rerun()
    col1, col2 = st.columns(2)
    if col1.button("Skip ⏭️"):
        state["index"] += 1
        st.rerun()
    if col2.button("End test now"):
        state["index"] = len(questions)
        st.rerun()
