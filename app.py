import io
import subprocess
import sys
import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import Session
from database.models import Business, Email, Person, ScrapingJob, SocialProfile
from services.pipeline import create_job, engine

st.set_page_config(page_title='ProspectLab | Lead workspace', page_icon='🔎', layout='wide')
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
st.sidebar.markdown('## 🔎 ProspectLab')
st.sidebar.caption('Lead intelligence workspace')
section = st.sidebar.radio('Workspace', ['Dashboard', 'Prospecting', 'Data management', 'Settings'])
menus = {'Dashboard':['Overview'], 'Prospecting':['Find people','Find companies','Directory search','Lead database'], 'Data management':['Jobs','Exports'], 'Settings':['Providers']}
page = st.sidebar.radio('Pages', menus[section])
if page == 'Find people': page='Decision-makers'
if page == 'Directory search': page='New search'
st.sidebar.divider()
st.sidebar.caption('Local data · No paid APIs')
st.markdown('<div class="eyebrow">Lead workspace</div>', unsafe_allow_html=True)
with Session(engine) as db:
    businesses = db.scalars(select(Business).order_by(Business.id.desc())).all()
    jobs = db.scalars(select(ScrapingJob).order_by(ScrapingJob.id.desc())).all()
    emails = db.scalars(select(Email)).all()
    socials = db.scalars(select(SocialProfile)).all()
    people = db.scalars(select(Person).order_by(Person.id.desc())).all()
    people_rows=[{k:getattr(p,k) for k in ('id','business_id','name','title','email','email_status','phone','city','state','linkedin','source','source_url')} for p in people]
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
        a,b,c,d,e = st.columns([2,1,1,1,1])
        query = a.text_input('Search name, address, phone or email', key=prefix+'query').casefold()
        state = b.selectbox('State', ['All'] + sorted({r['state'] for r in rows if r['state']}), key=prefix+'state')
        city = c.selectbox('City', ['All'] + sorted({r['city'] for r in rows if r['city']}), key=prefix+'city')
        source = d.selectbox('Source', ['All'] + sorted({r['source'] for r in rows if r['source']}), key=prefix+'source')
        niche = e.selectbox('Keyword', ['All'] + sorted({r['niche'] for r in rows if r['niche']}), key=prefix+'niche')
        f,g,h,i,j = st.columns(5)
        email = f.checkbox('Has email', key=prefix+'email')
        website = g.checkbox('Has website', key=prefix+'website')
        instagram = h.checkbox('Has Instagram', key=prefix+'instagram')
        facebook = i.checkbox('Has Facebook', key=prefix+'facebook')
        linkedin = j.checkbox('Has LinkedIn', key=prefix+'linkedin')
    return [r for r in rows if (not query or query in ' '.join(str(r[k]) for k in ('name','address','phone','emails')).casefold()) and (state=='All' or r['state']==state) and (city=='All' or r['city']==city) and (source=='All' or r['source']==source) and (niche=='All' or r['niche']==niche) and (not email or r['emails']) and (not website or r['website']) and (not instagram or r['instagram']) and (not facebook or r['facebook']) and (not linkedin or r['linkedin'])]
if page == 'Overview':
    st.title('Lead intelligence')
    st.caption('Track discovery, contact coverage and recent searches.')
    cols = st.columns(4)
    cols[0].metric('Businesses', len(rows)); cols[1].metric('With websites', sum(bool(r['website']) for r in rows)); cols[2].metric('With emails', sum(bool(r['emails']) for r in rows)); cols[3].metric('With social profiles', sum(any(r[p] for p in ('facebook','instagram','linkedin','tiktok','youtube','x','pinterest')) for r in rows))
    st.caption(f"{len(people_rows)} named people saved locally · {sum(p['email_status']=='verified' for p in people_rows)} provider-verified emails")
    a,b = st.columns([2,1])
    with a:
        st.subheader('Recent leads')
        for record in rows[:5]:
            with st.container(border=True):
                st.markdown('**'+record['name']+'**')
                st.caption(f"{record['city']}, {record['state']} · {record['source']}")
                st.write(record['phone'] or 'Phone not collected')
                st.write(record['emails'] or 'No published email collected')
                if record['website']: st.link_button('Company website',record['website'],key='overview_site'+str(record['id']))
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
        niche = st.text_input('Niche', placeholder='Coffee shops, law firms, salons…'); city = st.text_input('City', placeholder='Austin'); state = st.text_input('State', placeholder='TX'); keywords = st.text_input('Keywords · optional', placeholder='Independent, specialty coffee'); source = st.selectbox('Source', ['All sources', 'Google Maps', 'OpenStreetMap', 'Yelp']); limit = st.number_input('Maximum leads', 1, 1000, 100)
        st.caption('Searching the United States. All sources runs Google Maps, OpenStreetMap, and Yelp.')
        directory_url=st.text_input('Directory search URL · optional',placeholder='https://www.yelp.com/search?...')
        submitted = st.form_submit_button('Start search', type='primary')
    if submitted:
        if not city.strip() or not niche.strip(): st.error('Enter a niche and a US city.')
        else:
            try:
                search_terms = ' '.join(part.strip() for part in (niche, keywords) if part.strip())
                job_id = create_job(search_terms, city, state, source, int(limit), directory_url.strip(), 'United States')
                subprocess.Popen([sys.executable, 'main.py', '--resume', str(job_id)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                st.success(f'Job {job_id} started. See Jobs for status.')
            except ValueError as exc: st.error(str(exc))
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
    page_number = st.number_input('Page', min_value=1, max_value=max(1,(len(filtered)+7)//8), step=1)
    for record in filtered[(page_number-1)*8:page_number*8]:
        with st.container(border=True):
            st.subheader(record['name'])
            st.caption(f"{record['city']}, {record['state']}  ·  {record['source']}  ·  {record['status'].replace('_',' ')}")
            left,right=st.columns([3,2])
            with left:
                st.markdown('**Company details**')
                st.write(record['address'] or 'Address not collected')
                st.write('Phone:',record['phone'] or 'Not collected')
                if record['website']: st.link_button('Open company website',record['website'])
            with right:
                st.markdown('**Published business contacts**')
                st.write(record['emails'] or 'No published email collected')
                st.caption('These addresses are not verified decision-maker contacts.')
                st.link_button('View source listing',record['source_url'])
            with st.expander('Social profiles'):
                for platform in ('facebook','instagram','linkedin','tiktok','youtube','x','pinterest'):
                    if record[platform]: st.link_button(platform.title(),record[platform])
elif page == 'Providers':
    st.title('Data providers')
    st.caption('Connect eligible accounts. API access and free allowances depend on your actual plan.')
    with st.container(border=True):
        st.subheader('Apollo · People and roles')
        st.write('Search decision-makers by company domain and job title. Search does not reveal emails; enrichment is a separate credit-consuming action.')
        def keep_apollo_key(): st.session_state['apollo_credential']=st.session_state['apollo_key_input']
        st.text_input('Apollo API key',type='password',key='apollo_key_input',value=st.session_state.get('apollo_credential',''),on_change=keep_apollo_key,help='Held only in this browser session. Never committed or shown in exports.')
        st.link_button('Create or manage Apollo account','https://www.apollo.io/')
        st.link_button('Apollo API access and eligibility','https://docs.apollo.io/reference/apollo-api')
    with st.container(border=True):
        st.subheader('Apify · Website extraction')
        st.write('The supplied email-scraper actor collects website emails. It does not establish the person or role behind an address. Listed price: from $3.50 per 1,000 results; free platform usage is a dollar credit, not a guaranteed email count.')
        st.link_button('Review actor and pricing','https://apify.com/ib4ngz/email-scraper')
        st.caption('Not connected. Automatic paid Actor execution is disabled.')
    with st.container(border=True):
        st.subheader('Clay · Enrichment workflows')
        st.write('Account access, API availability and credits must be verified before enabling automated fallback.')
        st.link_button('Review Clay plans','https://www.clay.com/pricing')
        st.caption('Not connected.')
elif page == 'Decision-makers':
    st.title('Find people')
    st.caption('Search named people saved locally, or query an eligible Apollo account for more prospects.')
    with st.container(border=True):
        a,b,c=st.columns(3)
        name_filter=a.text_input('Name or job title',key='local_person_name').casefold()
        place_filter=b.text_input('City or state',key='local_person_place').casefold()
        company_filter=c.text_input('Company',key='local_person_company').casefold()
        company_names={r['id']:r['name'] for r in rows}
        local_people=[p for p in people_rows if name_filter in (p['name']+' '+p['title']).casefold() and place_filter in (p['city']+' '+p['state']).casefold() and company_filter in company_names.get(p['business_id'],'').casefold()]
        st.caption(f'{len(local_people)} saved people match')
        for p in local_people[:25]:
            with st.container(border=True):
                st.markdown(f"**{p['name']}** · {p['title'] or 'Role unavailable'}")
                st.caption(f"{company_names.get(p['business_id'],'Company unavailable')} · {p['city']}, {p['state']}")
                st.write('Email:',p['email'] or 'Unavailable',' · Status:',p['email_status'])
                st.write('Phone:',p['phone'] or 'Unavailable')
                st.link_button('Source',p['source_url'])
    st.subheader('Search Apollo people')
    with st.form('people_search'):
        left,right=st.columns(2)
        with left:
            roles=st.multiselect('Job titles',['Owner','Founder','CEO','CFO','CTO','Practice Manager','Office Manager','Managing Partner'],default=['Owner','Founder','CEO','Practice Manager'])
            custom_titles=st.text_input('Other titles',placeholder='Medical director, Operations manager')
            seniority=st.selectbox('Seniority',['Any','Owner','Founder','C Suite','VP','Director','Manager'])
        with right:
            domain=st.text_input('Company domain · optional',placeholder='company.com')
            location=st.text_input('Person location · optional',placeholder='Houston, TX')
            industry=st.text_input('Company industry · optional',placeholder='hospital & health care')
            email_status=st.selectbox('Provider email status',['Any','verified','unverified','unavailable'])
        submit=st.form_submit_button('Search people',type='primary')
    if submit:
        from services.people import search_people
        try:
            with st.spinner('Searching Apollo…'):
                titles=roles+[value.strip() for value in custom_titles.split(',') if value.strip()]
                st.session_state['people_results']=search_people(st.session_state.get('apollo_credential',''),domain,titles,location,industry,'' if seniority=='Any' else seniority.lower(),email_status='' if email_status=='Any' else email_status)
                from services.people_repository import save_apollo_people
                st.session_state['people_saved']=save_apollo_people(engine,st.session_state['people_results'])
        except Exception as exc: st.error(str(exc))
    for person in st.session_state.get('people_results',[]):
        with st.container(border=True):
            st.subheader(person.get('name') or ' '.join(filter(None,[person.get('first_name'),person.get('last_name_obfuscated')])) or 'Name restricted by provider')
            st.write(person.get('title') or 'Role unavailable')
            st.caption((person.get('organization') or {}).get('name',''))
            st.write('Email: requires separate enrichment')
    if st.session_state.get('people_saved'):
        st.success(f"{st.session_state['people_saved']} named people saved locally. Refresh to see them in the local list.")
    if 'people_results' in st.session_state and not st.session_state['people_results']: st.info('No people returned for this domain and role selection.')
elif page == 'Find companies':
    st.title('Find companies')
    st.caption('Browse locally discovered companies, then use Apollo when an eligible account is connected.')
    local_companies=lead_filters('companies')
    st.caption(f'{len(local_companies)} local companies match')
    for company in local_companies[:25]:
        with st.container(border=True):
            st.markdown(f"**{company['name']}** · {company['city']}, {company['state']}")
            st.caption(f"{company['category']} · {company['source']} · {company['status']}")
            st.write(company['website'] or 'Website unavailable',' · ',company['phone'] or 'Phone unavailable')
            st.link_button('Source listing',company['source_url'])
    st.subheader('Search Apollo companies')
    st.caption('Apollo charges one credit per results page for its organization search endpoint.')
    apollo_connected=bool(st.session_state.get('apollo_credential',''))
    if not apollo_connected:
        st.info('Apollo is not connected. Add an eligible API key under Settings → Providers before using paid-credit company search. Local company browsing above remains available.')
    with st.form('company_search'):
        a,b,c=st.columns(3)
        keyword=a.text_input('Industry or keyword',placeholder='coffee shops')
        location=b.text_input('Headquarters location',placeholder='Texas')
        domain=c.text_input('Domain · optional',placeholder='clinic.com')
        acknowledge=st.checkbox('Use one Apollo search credit for this page',disabled=not apollo_connected)
        submit=st.form_submit_button('Search companies',type='primary',disabled=not apollo_connected)
    if submit:
        if not acknowledge: st.error('Confirm the one-credit search cost first.')
        else:
            from services.people import search_companies
            try: st.session_state['company_results']=search_companies(st.session_state.get('apollo_credential',''),keyword,location,domain)
            except Exception as exc: st.error(str(exc))
    for company in st.session_state.get('company_results',[]):
        with st.container(border=True):
            st.subheader(company.get('name') or 'Unnamed company')
            st.caption(' · '.join(filter(None,[company.get('industry'),company.get('city'),company.get('state')])))
            st.write(company.get('website_url') or 'Website unavailable')
            st.write(company.get('phone') or 'Phone unavailable')
    if 'company_results' in st.session_state and not st.session_state['company_results']: st.info('No companies returned for these filters.')
elif page == 'Exports':
    st.title('Export leads')
    filtered = lead_filters('exports')
    email_only = st.checkbox('Only businesses with published emails')
    if email_only: filtered = [r for r in filtered if r['emails']]
    st.caption(f'{len(filtered)} records ready to export')
    frame = pd.DataFrame(filtered)
    if frame.empty: st.info('No leads match these filters.')
    else:
        st.download_button('Download CSV', frame.to_csv(index=False).encode('utf-8-sig'), 'prospect_leads.csv', 'text/csv')
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer: frame.to_excel(writer, index=False, sheet_name='Leads')
        st.download_button('Download XLSX', output.getvalue(), 'prospect_leads.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

