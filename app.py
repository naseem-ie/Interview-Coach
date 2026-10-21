"""Interview Coach - a daily challenge for the job you are preparing for."""

import time
from datetime import date

import streamlit as st

from notion_client import APIResponseError

from aptitude import APTITUDE_TOPICS, CHALLENGE_ID as APTITUDE_ID, TARGET_SECONDS, daily_aptitude

from notion_data import STATUSES, load_job_description, load_jobs, update_status
from progress import (
    XP_PER_CHALLENGE, XP_PER_CORRECT, XP_PER_LEVEL, answers_for_day, complete_challenge,
    connect, job_summary, level_for, question_history, readiness, recent_accuracy, record_answer,
    streak,
    topic_stats, total_xp,
)
from quiz import load_bank, pick_daily_questions, split_topics, topic_sizes, topics_for_job

st.set_page_config(page_title="Interview Coach", page_icon="🎯")
CLOSED = {"No reply - inactive", "Rejected", "Withdrawn"}
LETTERS = "ABCD"


@st.cache_data(ttl=300)
def get_jobs():
    """Load jobs from Notion, reusing the result for 5 minutes."""
    return load_jobs()


@st.cache_data(ttl=300)
def get_description(page_id):
    """Load the job advert written inside the job's Notion page."""
    return load_job_description(page_id)


@st.cache_data
def get_bank():
    """Load the question bank once."""
    return load_bank()


# ---------- Sidebar: pick a job ----------
with st.sidebar:
    st.header("🎯 Interview Coach")
    if st.button("🔄 Refresh from Notion"):
        get_jobs.clear()
    try:
        jobs = get_jobs()
    except Exception as error:
        st.error(f"Could not load jobs from Notion: {error}")
        st.stop()

    show_closed = st.checkbox("Show inactive, rejected and withdrawn jobs")
    visible = [job for job in jobs if show_closed or job["status"] not in CLOSED]
    if not visible:
        st.info("No open jobs. Tick the box above to see closed ones.")
        st.stop()

    index = st.selectbox(
        "Preparing for",
        options=range(len(visible)),
        format_func=lambda i: f"{visible[i]['company']} - {visible[i]['role']}",
    )
    job = visible[index]
    st.caption(f"Status: {job['status'] or 'Not set'}")

# ---------- Today's questions and progress ----------
bank = get_bank()
today = date.today()
conn = connect()

topic_ids = topics_for_job(job["skill_gaps"], bank["topics"])
technical, behavioural = split_topics(topic_ids)

# ---------- Header: this job ----------
st.title(job["company"])
st.caption(job["role"])

sizes = topic_sizes(bank)
summary = job_summary(conn, job["id"])

st.markdown("#### 🎯 Readiness for this job")
col1, col2, col3 = st.columns(3)
col1.metric("🛠️ Technical", f"{readiness(conn, technical, sizes)}%")
col2.metric("🗣️ Behavioural", f"{readiness(conn, behavioural, sizes)}%")
col3.metric(
    "✍️ All answers for this job",
    f"{summary['correct']} of {summary['answered']} correct",
)
st.caption(
    f"Readiness = share of this job's topic questions you have got right on your latest try. "
    f"You have earned {summary['xp']} XP and finished {summary['challenges']} "
    f"challenge(s) for this job."
)

with st.expander("📊 Topic breakdown: what to work on"):
    stats = topic_stats(conn, technical + behavioural, sizes)
    icons = {"Mastered": "✅", "Learning": "📘", "Not started": "⬜"}
    for topic_id, s in stats.items():
        name = bank["topics"][topic_id]["name"]
        st.write(
            f"{icons[s['status']]} **{name}**: {s['percent']}% "
            f"({s['correct']} of {s['total']} questions right) · {s['status']}"
        )
        st.progress(s["percent"] / 100)
    st.caption("A topic is mastered once you have got 80% of its questions right on your latest try.")

# ---------- Overall progress (all jobs) ----------
xp = total_xp(conn)
level_number, level_name, xp_into_level = level_for(xp)
days = streak(conn, today)
xp_to_next = XP_PER_LEVEL - xp_into_level
with st.container(border=True):
    st.caption("🌍 Overall progress across all jobs")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("🔥 Streak", f"{days} day" if days == 1 else f"{days} days")
    col2.metric(f"⭐ Level · {level_name}", level_number)
    col3.metric("💎 Total XP", xp)
    col4.metric("🧠 Aptitude", f"{recent_accuracy(conn, APTITUDE_ID)}%", help="Accuracy over your last 30 aptitude answers")
    st.progress(min(xp_into_level / XP_PER_LEVEL, 1.0), text=f"{xp_to_next} XP to the next level")

st.divider()

# ---------- Choose what to practise ----------
mode = st.radio(
    "What do you want to practise?",
    ["🛠️ Technical", "🗣️ Behavioural", "🧠 Aptitude"],
    horizontal=True,
)
mode_key = {"🛠": "technical", "🗣": "behavioural", "🧠": "aptitude"}[mode[0]]
history = question_history(conn, before=today)

if mode_key == "aptitude":
    st.caption(
        "Aptitude tests (like the CCAT or SHL) screen candidates before interviews. This set is "
        f"the same for every job: numerical, logical and verbal. Aim for under {TARGET_SECONDS} "
        "seconds a question."
    )
    challenge_id = APTITUDE_ID
    questions = daily_aptitude(bank, today, history=history)
else:
    practice_topics = technical if mode_key == "technical" else behavioural
    if mode_key == "technical" and not any(t != "behavioural" for t in topic_ids):
        st.info(
            "No technical skill gaps recorded for this job in Notion, so these are core support "
            "topics (ITIL, Linux, SQL). Add skill gaps in Notion to tailor them."
        )
    st.caption("Topics: " + " · ".join(bank["topics"][t]["name"] for t in practice_topics))
    challenge_id = f"{job['id']}:{mode_key}"
    questions = pick_daily_questions(bank, practice_topics, today, job_id=challenge_id, history=history)
answered = answers_for_day(conn, today, challenge_id)
done = [q for q in questions if q["id"] in answered]
remaining = [q for q in questions if q["id"] not in answered]

if not remaining:
    complete_challenge(conn, today, challenge_id)

# ---------- Today's challenge ----------
feedback = st.session_state.get("feedback")
if feedback and feedback["challenge_id"] != challenge_id:
    feedback = None

if feedback:
    # Show the result of the answer just given
    question = next(q for q in questions if q["id"] == feedback["question_id"])
    st.subheader(f"Question {len(done)} of {len(questions)}")
    st.write(question["question"])
    correct_letter = LETTERS[question["answer"]]
    if feedback["correct"]:
        st.success(f"✅ Correct! +{XP_PER_CORRECT} XP")
    else:
        st.error(f"❌ Not quite. You chose {feedback['chosen']}; the answer is {correct_letter}.")
    if mode_key == "aptitude":
        seconds = feedback.get("seconds", 0)
        pace = "✅ on pace" if seconds <= TARGET_SECONDS else "⚠️ slower than test pace"
        st.caption(f"⏱️ Answered in {seconds} s (target: under {TARGET_SECONDS} s) · {pace}")
    st.info(f"**Answer:** {question['options'][question['answer']]}\n\n{question['explanation']}")
    topic = bank["topics"][question["topic"]]
    st.markdown(f"📚 Study more: [{topic['name']}]({topic['study_link']})")

    label = "Next question ➡️" if remaining else "See today's results 🏁"
    if st.button(label, type="primary"):
        st.session_state.pop("feedback")
        if not remaining:
            st.session_state["celebrate"] = True
        st.rerun()

elif remaining:
    # Ask the next unanswered question
    question = remaining[0]
    started = st.session_state.setdefault("started", {})
    started.setdefault(question["id"], time.time())
    number = len(done) + 1
    st.subheader(f"Question {number} of {len(questions)}")
    st.progress(len(done) / len(questions))
    with st.container(border=True):
        st.caption(bank["topics"][question["topic"]]["name"])
        with st.form(f"form-{question['id']}"):
            st.markdown(f"**{question['question']}**")
            choice = st.radio(
                "Your answer",
                options=range(len(question["options"])),
                format_func=lambda i: f"{LETTERS[i]}) {question['options'][i]}",
                index=None,
            )
            submitted = st.form_submit_button("Submit answer", type="primary")
    if submitted:
        if choice is None:
            st.warning("Pick an answer first.")
        else:
            correct = choice == question["answer"]
            record_answer(conn, today, challenge_id, question, correct)
            seconds = time.time() - started.pop(question["id"], time.time())
            st.session_state["feedback"] = {
                "seconds": round(seconds),
                "challenge_id": challenge_id,
                "question_id": question["id"],
                "chosen": LETTERS[choice],
                "correct": correct,
            }
            st.rerun()

else:
    # Challenge finished for today
    if st.session_state.pop("celebrate", False):
        st.balloons()
    score = sum(answered[q["id"]] for q in questions)
    earned = score * XP_PER_CORRECT + XP_PER_CHALLENGE
    st.subheader("🏁 Today's challenge complete")
    st.write(
        f"You scored **{score} out of {len(questions)}** and earned **{earned} XP** "
        f"on this challenge ({score} × {XP_PER_CORRECT} for correct answers "
        f"+ {XP_PER_CHALLENGE} finishing bonus)."
    )
    missed = [q for q in questions if not answered[q["id"]]]
    if missed:
        st.markdown("**Worth revisiting** (these will come back soon):")
        for q in missed:
            topic = bank["topics"][q["topic"]]
            st.markdown(f"- {q['question']} ([{topic['name']}]({topic['study_link']}))")
    st.info("Come back tomorrow for a new set. Or choose another kind of practice above to keep going.")

conn.close()

# ---------- Job details ----------
st.divider()
st.subheader("📄 About this job")

with st.expander("Job description and requirements", expanded=False):
    try:
        description = get_description(job["id"])
    except Exception as error:
        description = ""
        st.warning(f"Could not load the description from Notion: {error}")
    if description:
        st.markdown(description)
    else:
        st.info(
            "No job description saved yet. Open this job in Notion and paste the job advert "
            "into the page, then click 🔄 Refresh from Notion."
        )
    if job["job_link"]:
        st.link_button("Open job posting", job["job_link"])

with st.expander("Your notes, next steps and contacts"):
    if job["next_action"]:
        st.write(f"**Next action:** {job['next_action']}")
    if job["follow_up_due"]:
        st.write(f"**Follow-up due:** {job['follow_up_due']}")
    if job["skill_gaps"]:
        st.write(f"**Skill gaps:** {job['skill_gaps']}")
    st.write(f"**Recruiter:** {job['recruiter'] or '-'}")
    st.write(f"**Salary:** {job['salary'] or '-'}")
    if job["notes"]:
        st.write(f"**Notes:** {job['notes']}")
    if job["prep_page"]:
        st.link_button("Open prep page in Notion", job["prep_page"])

with st.expander("✏️ Update status"):
    current = job["status"] if job["status"] in STATUSES else STATUSES[0]
    new_status = st.selectbox("Status", STATUSES, index=STATUSES.index(current))
    if st.button("Save to Notion", disabled=new_status == job["status"]):
        try:
            update_status(job["id"], new_status)
        except APIResponseError as error:
            if error.code == "restricted_resource":
                st.error(
                    "Your Notion connection is read-only. In Notion, open the Interview Coach "
                    "connection, tick 'Update content' and save, then try again."
                )
            else:
                st.error(f"Notion refused the change: {error}")
        else:
            get_jobs.clear()
            st.success(f"Saved: {job['company']} is now '{new_status}'.")
            st.rerun()
    st.caption("Inactive, rejected and withdrawn jobs are hidden unless you tick the box in the sidebar.")
