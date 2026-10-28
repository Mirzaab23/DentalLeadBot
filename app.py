import io
import subprocess
import sys
import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import Business, ScrapingJob
from services.pipeline import create_job, engine

st.set_page_config(page_title='DentalLeadBot', layout='wide')
st.title('DentalLeadBot')
st.caption('Local dental business discovery • OpenStreetMap data')
page = st.sidebar.radio('Navigation', ['Overview', 'New search', 'Jobs', 'Lead database', 'Exports'])
with Session(engine) as db:
    businesses = db.scalars(select(Business).order_by(Business.id.desc())).all()
    jobs = db.scalars(select(ScrapingJob).order_by(ScrapingJob.id.desc())).all()
    rows = [{k: getattr(b, k) for k in ('id', 'name', 'niche', 'category', 'address', 'city', 'state', 'phone', 'website', 'source', 'source_url', 'status')} for b in businesses]
    job_rows = [{k: getattr(j, k) for k in ('id', 'niche', 'city', 'state', 'source', 'target_count', 'discovered_count', 'processed_count', 'status', 'last_error')} for j in jobs]
frame = pd.DataFrame(rows)
if page == 'Overview':
    cols = st.columns(3)
    cols[0].metric('Businesses', len(rows)); cols[1].metric('With websites', sum(bool(r['website']) for r in rows)); cols[2].metric('Completed jobs', sum(j['status'] == 'completed' for j in job_rows))
    st.info('The current MVP discovers listings. Website enrichment is not yet connected.')
elif page == 'New search':
    with st.form('search'):
        niche = st.text_input('Niche', 'dentists'); city = st.text_input('City'); state = st.text_input('State', max_chars=2).upper(); limit = st.number_input('Maximum leads', 1, 1000, 100)
        submitted = st.form_submit_button('Start scraping')
    if submitted:
        if not city or len(state) != 2: st.error('Enter a city and two-letter state code.')
        else:
            job_id = create_job(niche, city, state, 'OpenStreetMap', int(limit))
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
    filtered = [r for r in rows if query in ' '.join(str(r[k]) for k in ('name', 'city', 'state')).lower()]
    st.dataframe(pd.DataFrame(filtered), use_container_width=True)
else:
    if frame.empty: st.info('No leads to export yet.')
    else:
        st.download_button('Download CSV', frame.to_csv(index=False).encode('utf-8-sig'), 'dental_leads.csv', 'text/csv')
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: frame.to_excel(writer, index=False, sheet_name='Leads')
        st.download_button('Download XLSX', output.getvalue(), 'dental_leads.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

