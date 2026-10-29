import io
import subprocess
import sys
import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import Business, Email, ScrapingJob, SocialProfile
from services.pipeline import create_job, engine

st.set_page_config(page_title='DentalLeadBot', layout='wide')
st.title('DentalLeadBot')
st.caption('Local dental business discovery')
page = st.sidebar.radio('Navigation', ['Overview', 'New search', 'Jobs', 'Lead database', 'Exports'])
with Session(engine) as db:
    businesses = db.scalars(select(Business).order_by(Business.id.desc())).all()
    jobs = db.scalars(select(ScrapingJob).order_by(ScrapingJob.id.desc())).all()
    emails = db.scalars(select(Email)).all()
    socials = db.scalars(select(SocialProfile)).all()
    email_map = {}
    social_map = {}
    for email in emails: email_map.setdefault(email.business_id, set()).add(email.email)
    for social in socials: social_map.setdefault(social.business_id, {})[social.platform] = social.profile_url
    rows = []
    for business in businesses:
        row = {k: getattr(business, k) for k in ('id', 'name', 'niche', 'category', 'address', 'city', 'state', 'phone', 'website', 'source', 'source_url', 'status')}
        row['emails'] = ', '.join(sorted(email_map.get(business.id, set())))
        for platform in ('facebook', 'instagram', 'linkedin', 'tiktok', 'youtube', 'x', 'pinterest'):
            row[platform] = social_map.get(business.id, {}).get(platform, '')
        rows.append(row)
    job_rows = [{k: getattr(j, k) for k in ('id', 'niche', 'city', 'state', 'source', 'target_count', 'discovered_count', 'processed_count', 'status', 'last_error')} for j in jobs]
frame = pd.DataFrame(rows)
if page == 'Overview':
    cols = st.columns(3)
    cols[0].metric('Businesses', len(rows)); cols[1].metric('With websites', sum(bool(r['website']) for r in rows)); cols[2].metric('Completed jobs', sum(j['status'] == 'completed' for j in job_rows))
    st.metric('With published emails', sum(bool(r['emails']) for r in rows))
elif page == 'New search':
    with st.form('search'):
        niche = st.text_input('Niche', 'dentists'); city = st.text_input('City'); state = st.text_input('State', max_chars=2).upper(); source = st.selectbox('Source', ['Google Maps', 'OpenStreetMap', 'Yelp']); limit = st.number_input('Maximum leads', 1, 1000, 100)
        submitted = st.form_submit_button('Start scraping')
    if submitted:
        if not city or len(state) != 2: st.error('Enter a city and two-letter state code.')
        else:
            job_id = create_job(niche, city, state, source, int(limit))
            subprocess.Popen([sys.executable, 'main.py', '--resume', str(job_id)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            st.success(f'Job {job_id} started. See Jobs for status.')
elif page == 'Jobs':
    st.button('Refresh')
    st.dataframe(pd.DataFrame(job_rows), use_container_width=True)
    if job_rows:
        selected = st.selectbox('Job', [j['id'] for j in job_rows])
        a, b = st.columns(2)
        if a.button('Request stop'):
            with Session(engine) as db:
                job = db.get(ScrapingJob, selected)
                if job.status == 'running': job.status = 'stop_requested'; db.commit()
            st.rerun()
        if b.button('Resume'):
            with Session(engine) as db:
                job = db.get(ScrapingJob, selected)
                if job.status in ('stopped', 'failed'):
                    job.status = 'pending'; db.commit()
                    subprocess.Popen([sys.executable, 'main.py', '--resume', str(selected)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            st.rerun()
elif page == 'Lead database':
    query = st.text_input('Search name, city or state').lower()
    state_filter = st.selectbox('State', ['All'] + sorted({r['state'] for r in rows if r['state']}))
    has_email = st.checkbox('Has email')
    has_website = st.checkbox('Has website')
    filtered = [r for r in rows if query in ' '.join(str(r[k]) for k in ('name', 'city', 'state')).lower() and (state_filter == 'All' or r['state'] == state_filter) and (not has_email or r['emails']) and (not has_website or r['website'])]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True)
else:
    if frame.empty: st.info('No leads to export yet.')
    else:
        st.download_button('Download CSV', frame.to_csv(index=False).encode('utf-8-sig'), 'dental_leads.csv', 'text/csv')
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: frame.to_excel(writer, index=False, sheet_name='Leads')
        st.download_button('Download XLSX', output.getvalue(), 'dental_leads.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

