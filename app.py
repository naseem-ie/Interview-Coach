"""Interview Coach - a daily challenge for the job you are preparing for."""

import os
import time
from datetime import date

import streamlit as st

from notion_client import APIResponseError

from backup import answers_csv, backup_folder, backup_now, backups, daily_backup, interviews_csv
from aptitude import CHALLENGE_ID as APTITUDE_ID, TARGET_SECONDS, daily_aptitude
from ai_practice import render_ai_practice
from interview_page import render_interview
from aptitude_page import render_extra, render_mock, render_tips, show_tip

from demo import DEMO_DB, demo_mode, load_sample_jobs, sample_description
from notion_data import STATUSES, load_job_description, load_jobs, update_status
from progress import (
    DB_FILE, XP_PER_CHALLENGE, XP_PER_CORRECT, XP_PER_LEVEL, ai_questions, ai_skill_stats,
    answers_for_day, combined_readiness, complete_challenge, connect, job_summary, level_for,
    question_history, readiness, recent_accuracy, record_answer, streak, topic_stats, total_xp,
)
from quiz import load_bank, pick_daily_questions, split_topics, topic_sizes, topics_for_job, uncovered_gaps

st.set_page_config(page_title="Interview Coach", page_icon="🎯")
DEMO = demo_mode()
CLOSED = {"No reply - inactive", "Rejected", "Withdrawn"}
LETTERS = "ABCD"


@st.cache_data(ttl=300)
def get_jobs():
    """Load jobs from Notion (or the sample jobs in demo mode), reusing the result for 5 minutes."""
    return load_sample_jobs() if DEMO else load_jobs()


@st.cache_data(ttl=300)
def get_description(page_id):
    """Load the job advert written inside the job's Notion page."""
    return sample_description(page_id) if DEMO else load_job_description(page_id)


@st.cache_data
def get_bank():
    """Load the question bank once."""
    return load_bank()


# ---------- Sidebar: pick a job ----------
with st.sidebar:
    st.header("🎯 Interview Coach")
    if DEMO:
        st.info(
            "🧪 **Demo mode**: made-up sample jobs and separate demo progress. "
            "Add your Notion key to .env to use your own jobs."
        )
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
conn = connect(DEMO_DB if DEMO else DB_FILE)

# ---------- Sidebar: backup and export ----------
if not DEMO:  # demo progress is throwaway, so it is not backed up
    with st.sidebar:
        folder = backup_folder()
        if not st.session_state.get("backup_checked"):
            st.session_state["backup_checked"] = True
            try:
                if daily_backup(DB_FILE, folder, today):
                    st.toast("💾 Today's backup saved")
            except OSError as error:
                st.warning(f"Daily backup failed: {error}")
        with st.expander("💾 Backup & export"):
            st.caption(
                "Your progress is backed up **automatically** once a day to this folder "
                "(OneDrive keeps it safe in the cloud). You don't need to do anything."
            )
            st.code(str(folder), language=None)
            saved = backups(folder)
            latest = saved[0].stem.removeprefix("progress-") if saved else "none yet"
            st.caption(f"Latest backup: {latest} · {len(saved)} kept (newest 10)")
            col1, col2 = st.columns(2)
            if col1.button("Back up now"):
                try:
                    saved = [backup_now(DB_FILE, folder, today)]
                    st.success(f"Saved {saved[0].name}")
                except OSError as error:
                    st.error(f"Backup failed: {error}")
            if hasattr(os, "startfile") and col2.button("📂 Open folder"):
                folder.mkdir(parents=True, exist_ok=True)
                os.startfile(folder)  # opens File Explorer (Windows only)
            if saved:
                st.download_button(
                    "📥 Download a backup copy", saved[0].read_bytes(), file_name=saved[0].name,
                    mime="application/octet-stream",
                )
            names = {j["id"]: f"{j['company']} - {j['role']}" for j in jobs}
            st.download_button(
                "📥 My answers (CSV)", answers_csv(conn, names).encode("utf-8-sig"),
                file_name=f"interview-coach-answers-{today}.csv", mime="text/csv",
            )
            st.download_button(
                "📥 My mock interviews (CSV)", interviews_csv(conn, names).encode("utf-8-sig"),
                file_name=f"interview-coach-interviews-{today}.csv", mime="text/csv",
            )
            st.caption(
                "**To restore on a new laptop:** close the app, copy the newest backup into the "
                "project folder, rename it to progress.db, then start the app."
            )

topic_ids = topics_for_job(job["skill_gaps"], bank["topics"])
technical, behavioural = split_topics(topic_ids)
gaps = uncovered_gaps(job["skill_gaps"], bank["topics"])
ai_pool = ai_questions(conn, gaps, job["id"])

# ---------- Header: this job ----------
st.title(job["company"])
st.caption(job["role"])

sizes = topic_sizes(bank)
summary = job_summary(conn, job["id"])

st.markdown("#### 🎯 Readiness for this job")
col1, col2, col3 = st.columns(3)
technical_stats = topic_stats(conn, technical, sizes)
ai_stats = ai_skill_stats(conn, ai_pool)
col1.metric("🛠️ Technical", f"{combined_readiness(technical_stats, ai_stats)}%")
col2.metric("🗣️ Behavioural", f"{readiness(conn, behavioural, sizes)}%")
col3.metric(
    "✍️ All answers for this job",
    f"{summary['correct']} of {summary['answered']} correct",
)
st.caption(
    f"Readiness = share of this job's questions (question bank + 🤖 AI practice) you have got "
    f"right on your latest try. "
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
    for skill, s in ai_stats.items():
        st.write(
            f"{icons[s['status']]} 🤖 **{skill}**: {s['percent']}% "
            f"({s['correct']} of {s['total']} AI questions right) · {s['status']}"
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
    ["🛠️ Technical", "🗣️ Behavioural", "🧠 Aptitude", "🎤 Mock interview"],
    horizontal=True,
)
mode_key = {"🛠": "technical", "🗣": "behavioural", "🧠": "aptitude", "🎤": "interview"}[mode[0]]
history = question_history(conn, before=today)

run_daily = True
if mode_key == "interview":
    render_interview(conn, today, job)
    run_daily = False
elif mode_key == "aptitude":
    st.caption(
        "Aptitude tests (like the CCAT or SHL) often arrive without warning before interviews. "
        "They are the same for every job: numerical, logical and verbal."
    )
    activity = st.radio(
        "Aptitude practice",
        ["📅 Daily 6", "➕ Practise more", "⏱️ Timed mock test", "📘 Tips & tricks"],
        horizontal=True,
        label_visibility="collapsed",
    )
    if activity == "➕ Practise more":
        render_extra(bank, conn, today)
        run_daily = False
    elif activity == "⏱️ Timed mock test":
        render_mock(bank, conn, today)
        run_daily = False
    elif activity == "📘 Tips & tricks":
        render_tips(bank)
        run_daily = False
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
    if mode_key == "technical":
        if gaps:
            st.caption("⚠️ Not in the question bank yet: " + " · ".join(gaps))
        technical_activity = st.radio(
            "Technical practice",
            ["📅 Daily 5", "🤖 AI practice"],
            horizontal=True,
            label_visibility="collapsed",
        )
        if technical_activity == "🤖 AI practice":
            render_ai_practice(conn, today, job, gaps)
            run_daily = False
    challenge_id = f"{job['id']}:{mode_key}"
    questions = pick_daily_questions(bank, practice_topics, today, job_id=challenge_id, history=history)
if run_daily:
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
        if mode_key == "aptitude":
            show_tip(question)
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
        if mode_key == "aptitude":
            st.info("Come back tomorrow for a new set, or choose ➕ Practise more or ⏱️ Timed mock test above.")
        else:
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
        if DEMO:
            st.info("Demo mode: sample jobs can't be changed. With your own Notion key, this saves to Notion.")
            st.stop()
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
