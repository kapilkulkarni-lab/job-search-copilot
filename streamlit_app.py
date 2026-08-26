import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from jobcopilot import db, pipeline
from jobcopilot.claude_client import build_profile_system_block, get_client
from jobcopilot.models import Application
from jobcopilot.sources import manual
from jobcopilot.tailor import draft_materials

load_dotenv()
st.set_page_config(page_title="Job Search Copilot", layout="wide")

config = pipeline.load_config()
conn = pipeline.get_connection(config)


@st.cache_resource
def _client():
    return get_client()


client = _client()
profile_system = build_profile_system_block(config["profile"])

st.title("Job Search Copilot")

with st.sidebar:
    st.header("Refresh postings")
    st.caption(
        "The morning digest already fetches and scores new postings automatically. "
        "Use this to pull immediately instead of waiting."
    )
    if st.button("Fetch & score new postings"):
        with st.spinner("Fetching..."):
            jobs, fetch_warnings = pipeline.fetch_all_jobs(config)
        with st.spinner(f"Scoring {len(jobs)} candidate posting(s)..."):
            scored, score_warnings = pipeline.ingest_and_score_new(
                conn, client, config["profile"], jobs
            )
        st.success(f"Scored {len(scored)} new posting(s).")
        for w in fetch_warnings + score_warnings:
            st.warning(w)

    st.divider()
    st.header("Add a job manually")
    st.caption("For postings on sites without a public API (e.g. Workday).")
    with st.form("manual_job_form", clear_on_submit=True):
        m_title = st.text_input("Title")
        m_company = st.text_input("Company")
        m_location = st.text_input("Location")
        m_url = st.text_input("URL")
        m_description = st.text_area("Description (paste the posting text)")
        if st.form_submit_button("Add & score") and m_title and m_description:
            job = manual.make_job(m_title, m_company, m_location, m_url, m_description)
            with st.spinner("Scoring..."):
                _, warnings = pipeline.ingest_and_score_new(
                    conn, client, config["profile"], [job]
                )
            for w in warnings:
                st.warning(w)
            st.success("Added.")

search_tab, applications_tab = st.tabs(["Search", "Applications"])

with search_tab:
    scored_jobs = db.get_scored_jobs(conn)
    st.caption(f"{len(scored_jobs)} scored posting(s) in the cache.")

    for sj in scored_jobs:
        job = sj.job
        with st.expander(f"{sj.score}  —  {job.title} @ {job.company} ({job.location})"):
            st.write(sj.rationale)
            if sj.matched_skills:
                st.caption("Matches: " + ", ".join(sj.matched_skills))
            st.markdown(f"[View posting]({job.url})")
            st.text_area("Description", job.description, height=150, key=f"desc_{job.key}",
                         disabled=True)

            draft_key = f"draft_{job.key}"
            if st.button("Draft resume bullets + cover letter", key=f"draft_btn_{job.key}"):
                with st.spinner("Drafting..."):
                    st.session_state[draft_key] = draft_materials(client, profile_system, job)

            existing_app = db.get_application(conn, job.key)
            draft = st.session_state.get(draft_key)
            default_bullets = (draft or {}).get("resume_bullets", "") or \
                (existing_app.resume_bullets if existing_app else "")
            default_letter = (draft or {}).get("cover_letter", "") or \
                (existing_app.cover_letter if existing_app else "")

            bullets = st.text_area("Resume bullets", default_bullets, height=150,
                                    key=f"bullets_{job.key}")
            letter = st.text_area("Cover letter draft", default_letter, height=200,
                                   key=f"letter_{job.key}")

            status_options = ["Not Applied", "Applied", "Interview", "Offer", "Rejected"]
            current_status = existing_app.status if existing_app else "Not Applied"
            status = st.selectbox("Status", status_options,
                                   index=status_options.index(current_status),
                                   key=f"status_{job.key}")

            if st.button("Save to tracker", key=f"save_{job.key}"):
                db.upsert_application(conn, Application(
                    job_key=job.key, company=job.company, title=job.title, status=status,
                    resume_bullets=bullets, cover_letter=letter,
                    applied_date=existing_app.applied_date if existing_app else "",
                    follow_up_date=existing_app.follow_up_date if existing_app else "",
                    notes=existing_app.notes if existing_app else "",
                ))
                st.success("Saved.")

with applications_tab:
    applications = db.get_applications(conn)
    if not applications:
        st.info("No applications tracked yet — save one from the Search tab.")
    else:
        rows = [{
            "job_key": a.job_key, "Company": a.company, "Title": a.title, "Status": a.status,
            "Applied": a.applied_date, "Follow-up": a.follow_up_date, "Notes": a.notes,
        } for a in applications]
        df = pd.DataFrame(rows)
        edited = st.data_editor(
            df,
            column_config={
                "job_key": None,
                "Status": st.column_config.SelectboxColumn(
                    options=["Not Applied", "Applied", "Interview", "Offer", "Rejected"]
                ),
            },
            disabled=["Company", "Title"],
            hide_index=True,
            key="applications_editor",
        )
        if st.button("Save changes"):
            by_key = {a.job_key: a for a in applications}
            for _, row in edited.iterrows():
                app = by_key[row["job_key"]]
                app.status = row["Status"]
                app.applied_date = row["Applied"]
                app.follow_up_date = row["Follow-up"]
                app.notes = row["Notes"]
                db.upsert_application(conn, app)
            st.success("Saved.")
