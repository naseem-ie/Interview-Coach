"""Interview Coach - pick a job from your Notion tracker to prepare for."""

import streamlit as st

from notion_data import load_jobs

st.set_page_config(page_title="Interview Coach", page_icon="🎯")
st.title("🎯 Interview Coach")
st.caption("Pick a job from your Notion tracker to prepare for.")


@st.cache_data(ttl=300)
def get_jobs():
    """Load jobs from Notion, reusing the result for 5 minutes."""
    return load_jobs()


if st.button("🔄 Refresh from Notion"):
    get_jobs.clear()

try:
    jobs = get_jobs()
except Exception as error:
    st.error(f"Could not load jobs from Notion: {error}")
    st.stop()

# Hide closed jobs unless the box is ticked
show_closed = st.checkbox("Show inactive, rejected and withdrawn jobs")
closed = {"No reply - inactive", "Rejected", "Withdrawn"}
visible = [job for job in jobs if show_closed or job["status"] not in closed]

if not visible:
    st.info("No open jobs. Tick the box above to see closed ones.")
    st.stop()

st.write(f"Showing **{len(visible)}** of {len(jobs)} jobs")

index = st.selectbox(
    "Which job are you preparing for?",
    options=range(len(visible)),
    format_func=lambda i: f"{visible[i]['company']} - {visible[i]['role']}",
)
job = visible[index]

# ---- Job details ----
st.subheader(job["company"])
st.write(job["role"])

col1, col2, col3 = st.columns(3)
col1.markdown(f"**Status**  \n{job['status'] or 'Not set'}")
col2.markdown(f"**Prep status**  \n{job['prep_status'] or 'Not set'}")
col3.metric("Match score", job["match_score"] if job["match_score"] is not None else "-")

if job["next_action"]:
    st.info(f"**Next action:** {job['next_action']}")
if job["follow_up_due"]:
    st.write(f"📅 Follow-up due: {job['follow_up_due']}")

st.markdown("#### Skill gaps to study")
if job["skill_gaps"]:
    for gap in job["skill_gaps"].split(";"):
        st.markdown(f"- {gap.strip()}")
else:
    st.write("None recorded yet. Add them in the Skill gaps column in Notion.")

with st.expander("More details"):
    st.write(f"**Applied:** {job['applied_date'] or '-'}")
    st.write(f"**Recruiter:** {job['recruiter'] or '-'}")
    st.write(f"**Salary:** {job['salary'] or '-'}")
    st.write(f"**Notes:** {job['notes'] or '-'}")
    if job["job_link"]:
        st.link_button("Open job posting", job["job_link"])
    if job["prep_page"]:
        st.link_button("Open prep page in Notion", job["prep_page"])