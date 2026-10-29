import io
import subprocess
import sys
import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import Business, Email, ScrapingJob, SocialProfile
from services.pipeline import create_job, engine

st.set_page_config(page_title='DentalLeadBot | Lead workspace', page_icon='🦷', layout='wide')
st.markdown('''<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
html,body,[data-testid="stApp"] {font-family:'DM Sans',sans-serif;background:#f4f7fb;color:#192a42}
[data-testid="stSidebar"] {background:#111f36}
[data-testid="stSidebar"] * {color:#eef3fc!important}
.block-container {padding-top:2rem;max-width:1450px}
h1,h2,h3 {color:#172940;letter-spacing:-.025em}
div[data-testid="stMetric"] {background:white;padding:20px;border:1px solid #e1e9f2;border-radius:14px;box-shadow:0 4px 16px #223b5909}
div[data-testid="stMetric"] * {color:#192a42!important}
div[data-testid="stDataFrame"] {border:1px solid #dfe7f0;border-radius:12px;overflow:hidden}
div.stButton button[kind="primary"],div.stFormSubmitButton button[kind="primary"] {background:#2259d5;color:white;border-radius:9px}
div.stButton button,div.stDownloadButton button {border-radius:9px}
.eyebrow {text-transform:uppercase;letter-spacing:.12em;font-size:.72rem;font-weight:700;color:#5b75a0}
</style>''', unsafe_allow_html=True)
st.sidebar.markdown('## 🦷 DentalLeadBot')
st.sidebar.caption('Lead intelligence workspace')
page = st.sidebar.radio('Workspace', ['Overview', 'New search', 'Jobs', 'Lead database', 'Exports'])
st.sidebar.divider()
st.sidebar.caption('Local data · No paid APIs')
st.markdown('<div class="eyebrow">Lead workspace</div>', unsafe_allow_html=True)
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
    job_rows = [{k: getattr(j, k) for k in ('id', 'niche', 'city', 'state', 'source', 'target_count', 'discovered_count', 'processed_count', 'email_found_count', 'status', 'last_error')} for j in jobs]
frame = pd.DataFrame(rows)
def lead_filters(prefix):
    with st.container(border=True):
        st.markdown('#### Find leads')
        a,b,c,d = st.columns([2,1,1,1])
        query = a.text_input('Search name, address, phone or email', key=prefix+'query').casefold()
        state = b.selectbox('State', ['All'] + sorted({r['state'] for r in rows if r['state']}), key=prefix+'state')
        city = c.selectbox('City', ['All'] + sorted({r['city'] for r in rows if r['city']}), key=prefix+'city')
        source = d.selectbox('Source', ['All'] + sorted({r['source'] for r in rows if r['source']}), key=prefix+'source')
        e,f,g,h,i = st.columns(5)
        email = e.checkbox('Has email', key=prefix+'email')
        website = f.checkbox('Has website', key=prefix+'website')
        instagram = g.checkbox('Has Instagram', key=prefix+'instagram')
        facebook = h.checkbox('Has Facebook', key=prefix+'facebook')
        linkedin = i.checkbox('Has LinkedIn', key=prefix+'linkedin')
    return [r for r in rows if (not query or query in ' '.join(str(r[k]) for k in ('name','address','phone','emails')).casefold()) and (state=='All' or r['state']==state) and (city=='All' or r['city']==city) and (source=='All' or r['source']==source) and (not email or r['emails']) and (not website or r['website']) and (not instagram or r['instagram']) and (not facebook or r['facebook']) and (not linkedin or r['linkedin'])]
if page == 'Overview':
    st.title('Lead intelligence')
    st.caption('Track discovery, contact coverage and recent searches.')
    cols = st.columns(4)
    cols[0].metric('Businesses', len(rows)); cols[1].metric('With websites', sum(bool(r['website']) for r in rows)); cols[2].metric('With emails', sum(bool(r['emails']) for r in rows)); cols[3].metric('With social profiles', sum(any(r[p] for p in ('facebook','instagram','linkedin','tiktok','youtube','x','pinterest')) for r in rows))
    a,b = st.columns([2,1])
    with a:
        st.subheader('Recent leads')
        preview = pd.DataFrame(rows[:10], columns=['name','city','state','phone','website','emails','source','status'])
        st.dataframe(preview.replace('', 'Not found'), hide_index=True, use_container_width=True)
        st.caption('Not found means no verified value has been collected. Check the status column for enrichment progress.')
    with b:
        st.subheader('Recent jobs')
        for job in job_rows[:5]:
            with st.container(border=True):
                st.write(f"**#{job['id']} · {job['city']}, {job['state']}**")
                st.caption(f"{job['source']} · {job['status']} · {job['processed_count']} processed")
elif page == 'New search':
    st.title('Create a lead search')
    st.caption('Discover businesses, then inspect their official websites for published contacts.')
    with st.form('search'):
        niche = st.text_input('Niche', 'dentists'); city = st.text_input('City'); state = st.text_input('State', max_chars=2).upper(); source = st.selectbox('Source', ['All sources', 'Google Maps', 'OpenStreetMap', 'Yelp']); limit = st.number_input('Maximum leads', 1, 1000, 100)
        submitted = st.form_submit_button('Start search', type='primary')
    if submitted:
        if not city or len(state) != 2: st.error('Enter a city and two-letter state code.')
        else:
            job_id = create_job(niche, city, state, source, int(limit))
            subprocess.Popen([sys.executable, 'main.py', '--resume', str(job_id)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            st.success(f'Job {job_id} started. See Jobs for status.')
elif page == 'Jobs':
    st.title('Jobs & progress')
    st.button('Refresh')
    for job in job_rows:
        with st.expander(f"#{job['id']} · {job['niche']} in {job['city']}, {job['state']} · {job['status']}"):
            a,b,c=st.columns(3)
            a.metric('Discovered',job['discovered_count']); b.metric('Processed',job['processed_count']); c.metric('Emails found',job['email_found_count'])
            st.progress(min(1.0,job['processed_count']/max(1,job['target_count'])))
            if job['status']=='completed' and job['discovered_count']<job['target_count']:
                st.info(f"Source returned {job['discovered_count']} accessible listings out of {job['target_count']} requested. Public search results may be limited.")
            if job['last_error']: st.error(job['last_error'])
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
    st.title('Lead database')
    filtered = lead_filters('leads')
    st.caption(f'{len(filtered)} of {len(rows)} businesses')
    st.dataframe(pd.DataFrame(filtered, columns=['name','city','state','category','phone','website','emails','instagram','facebook','linkedin','source','status']), hide_index=True, use_container_width=True, height=500)
    if filtered:
        selected = st.selectbox('Inspect lead', [f"{r['id']} · {r['name']}" for r in filtered])
        record = next(r for r in filtered if str(r['id']) == selected.split(' · ')[0])
        with st.container(border=True):
            st.subheader(record['name'])
            st.write(record['address'] or 'Address unavailable')
            st.write('Phone:', record['phone'] or 'Unavailable', ' | Email:', record['emails'] or 'No published email')
            st.write('Source:', record['source_url'])
            if record['website']: st.write('Website:',record['website'])
else:
    st.title('Export leads')
    filtered = lead_filters('exports')
    email_only = st.checkbox('Only businesses with published emails')
    if email_only: filtered = [r for r in filtered if r['emails']]
    st.caption(f'{len(filtered)} records ready to export')
    frame = pd.DataFrame(filtered)
    if frame.empty: st.info('No leads match these filters.')
    else:
        st.download_button('Download CSV', frame.to_csv(index=False).encode('utf-8-sig'), 'dental_leads.csv', 'text/csv')
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: frame.to_excel(writer, index=False, sheet_name='Leads')
        st.download_button('Download XLSX', output.getvalue(), 'dental_leads.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

