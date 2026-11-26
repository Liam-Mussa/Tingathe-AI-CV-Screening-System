import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { Chip, Field, Select, Person, Stat, Bar, Table, Head, Ring, VCard, LinkBtn, statusKind } from '../ui.jsx'
import { APP_STATUS, FIXED_SCORING_CRITERIA } from '../data.js'
import { useStore } from '../store.js'
import { apiApplicationToClient, downloadProtected, request } from '../api.js'

export const Dashboard = () => {
  const [{ applications, audit, vacancies }] = useStore()
  const open = vacancies.filter(v => v.status === 'Open')
  const attention = applications.filter(a => a.ext === 'Review' || a.decision === 'Undecided')
  const decided = applications.filter(a => a.decision !== 'Undecided' && a.decision !== 'Manual check')
  const recent = [...applications].sort((a, b) => String(b.createdAt || '').localeCompare(String(a.createdAt || ''))).slice(0, 5)
  return <>
  <div className="herocard"><div><h1>Good morning, Director</h1><p>{attention.length} application{attention.length === 1 ? '' : 's'} need your attention. {decided.length} decision{decided.length === 1 ? '' : 's'} recorded so far.</p></div><LinkBtn to="/admin/applications" k="gold">Review applications</LinkBtn></div>
  <div className="g4"><Stat i="briefcase" l="Open vacancies" v={open.length} n="currently accepting applications" /><Stat i="files" l="Applications" v={applications.length} n="all vacancies" /><Stat i="shield" l="Need attention" v={attention.length} n="extraction warnings" /><Stat i="users" l="Decisions recorded" v={decided.length} n="this cycle" /></div>
  <div className="g2"><div className="card"><h3 style={{ marginBottom: 16 }}>Screening pipeline</h3><div className="col">{APP_STATUS.map((label, s) => { const n = applications.filter(a => a.status === s).length; const p = applications.length ? n / applications.length * 100 : 0
    return <div className="row" key={label}><span style={{ width: 110, fontSize: 13.5 }}>{label}</span><Bar p={p} /><b>{n}</b></div> })}</div></div>
    <div className="card"><h3 style={{ marginBottom: 8 }}>Closing soon</h3>{open.map(v => { const n = applications.filter(a => a.vacancyId === v.id).length
      return <div className="mini" key={v.id}><img src={`/images/${v.img}.svg`} alt="" /><div style={{ flex: 1 }}><b>{v.title}</b><br /><span className="mut">Closes {v.closes}</span></div><Chip k="b">{n} applicants</Chip></div> })}</div></div>
  <div className="card"><h3 style={{ marginBottom: 12 }}>Recent applications</h3>{recent.length === 0 ? <p className="mut p0">No applications yet. New applications appear here as soon as they are submitted.</p> :
    <Table head={['Applicant', 'Vacancy', 'Status', '']} rows={recent.map(a => { const v = vacancies.find(x => x.id === a.vacancyId); return [<Person n={a.name} />, v?.title || '—', <Chip k={statusKind(a.ext)}>{a.ext === 'Review' ? 'Needs review' : APP_STATUS[a.status]}</Chip>, <Link to={`/admin/applications/${a.id}`}>Open</Link>] })} />}</div>
  <div className="card"><h3 style={{ marginBottom: 12 }}>Recent activity</h3>{audit.length === 0 ? <p className="mut p0">Nothing recorded yet.</p> : <Table head={['Who', 'Action', 'Item']} rows={audit.slice(0, 5).map(a => [<Chip k={a[0] === 'System' ? 'n' : 'b'}>{a[0]}</Chip>, a[1], a[2]])} />}</div></>
}

export function Notifications() {
  const [{ notifications, error }, { loadNotifications, markNotificationRead }] = useStore()
  const [actionError, setActionError] = useState('')
  useEffect(() => {
    loadNotifications()
  }, [loadNotifications])

  const markRead = async notification => {
    setActionError('')
    try {
      await markNotificationRead(notification.id)
    } catch (requestError) {
      setActionError(requestError.message)
    }
  }

  return <><Head title="Notifications" sub="Updates about your recruitment account">
    <button className="btn o" type="button" onClick={loadNotifications}>Refresh</button>
  </Head>
    {(actionError || error) && <p className="card" role="alert" style={{ color: '#9B2C1F' }}>{actionError || error}</p>}
    {!error && notifications.length === 0 && <div className="card"><p className="mut p0">You have no notifications yet.</p></div>}
    {notifications.length > 0 && <div className="col">{notifications.map(notification => <article className="card notification-card" key={notification.id}>
        <div className="row sp"><div className="row"><h3>{notification.title}</h3>{!notification.is_read && <Chip k="b">New</Chip>}</div>
          {notification.created_at && <time className="mut">{new Date(notification.created_at).toLocaleString()}</time>}</div>
        <p className="mut p0">{notification.message}</p>
        {!notification.is_read && <button className="btn o sm" type="button" onClick={() => markRead(notification)}>Mark as read</button>}
      </article>)}</div>}
  </>
}

export function AdminSearch() {
  const [{ applications, vacancies }] = useStore()
  const [params] = useSearchParams()
  const query = (params.get('q') || '').trim().toLocaleLowerCase()
  const matchingApplications = query ? applications.filter(application => [
    application.name,
    application.email,
    application.phone,
    application.district,
    application.note,
    application.vacancy_title,
    ...(application.criterionScores || []).flatMap(score => [score.label, score.evidence]),
  ].some(value => String(value || '').toLocaleLowerCase().includes(query))) : []
  const matchingVacancies = query ? vacancies.filter(vacancy => [
    vacancy.title,
    vacancy.cat,
    vacancy.summary,
    vacancy.description,
    ...(vacancy.criteria || []).flatMap(criterion => [criterion[0], criterion[2]?.required_value]),
  ].some(value => String(value || '').toLocaleLowerCase().includes(query))) : []

  return <><Head title="Search" sub={query ? `Results for “${params.get('q')}”` : 'Search applicants and vacancies'} />
    {!query && <div className="card"><p className="mut p0">Enter a name, phone, district, vacancy, subject or requirement in the search bar.</p></div>}
    {query && <div className="g2">
      <section className="card col"><h2>Applicants ({matchingApplications.length})</h2>
        {matchingApplications.map(application => <Link className="search-result" key={application.id} to={`/admin/applications/${application.id}`}><b>{application.name}</b><span>{application.vacancy_title || 'Application'} · {application.district || 'District not listed'} · Score {application.score ?? 'Not scored'}</span></Link>)}
        {matchingApplications.length === 0 && <p className="mut p0">No matching applicants.</p>}
      </section>
      <section className="card col"><h2>Vacancies ({matchingVacancies.length})</h2>
        {matchingVacancies.map(vacancy => <Link className="search-result" key={vacancy.id} to={`/admin/vacancies/${vacancy.id}`}><b>{vacancy.title}</b><span>{vacancy.cat} · {vacancy.status}</span><span>{vacancy.summary}</span></Link>)}
        {matchingVacancies.length === 0 && <p className="mut p0">No matching vacancies.</p>}
      </section>
    </div>}</>
}

export const Vacancies = () => {
  const [{ vacancies }, { loadVacancies }] = useStore()
  const removeVacancy = v => {
    if (!window.confirm(`Delete vacancy "${v.title}"? This will also remove related applications. This cannot be undone.`)) return
    request(`/api/vacancies/${v.id}`, { method: 'DELETE' }).then(() => { window.alert('Vacancy deleted successfully.'); loadVacancies() }).catch(error => window.alert(error.message))
  }
  const closeVacancy = v => {
    if (!window.confirm(`Close vacancy "${v.title}"? Applicants will no longer be able to submit applications.`)) return
    request(`/api/vacancies/${v.id}/close`, { method: 'POST' }).then(() => { window.alert('Vacancy closed successfully.'); loadVacancies() }).catch(error => window.alert(error.message))
  }
  const reopenVacancy = v => {
    if (!window.confirm(`Reopen vacancy "${v.title}"?`)) return
    request(`/api/vacancies/${v.id}/reopen`, { method: 'POST' }).then(() => { window.alert('Vacancy reopened successfully.'); loadVacancies() }).catch(error => window.alert(error.message))
  }
  const [tab, setTab] = useState('All'); const rows = vacancies.filter(v => tab === 'All' || v.status === tab)
  return <><Head title="Vacancies" sub="Create, publish and close vacancies"><LinkBtn to="/admin/vacancies/new">New vacancy</LinkBtn></Head>
    <div className="tabs">{['All', 'Open', 'Draft', 'Closed'].map(t => <a key={t} href="#" className={t === tab ? 'on' : ''} onClick={e => { e.preventDefault(); setTab(t) }}>{t}</a>)}</div>
    <div className="vgrid">{rows.map(v => <div className="col" key={v.id}><VCard v={v} admin to={`/admin/vacancies/${v.id}`} /><button className="btn o" type="button" onClick={() => removeVacancy(v)}>Delete vacancy</button>
      {v.status === 'Open' ? <button className="btn" type="button" onClick={() => closeVacancy(v)}>Close vacancy</button> : v.status === 'Closed' ? <button className="btn" type="button" onClick={() => reopenVacancy(v)}>Reopen vacancy</button> : null}</div>)}<Link to="/admin/vacancies/new" className="vnew">+ New vacancy</Link></div></>
}

export function VacancyBuilder() {
  const [{ vacancies }] = useStore()
  const { id } = useParams()
  const existing = vacancies.find(v => String(v.id) === String(id))
  const valueFor = label => existing?.criteria?.find(item => item[0] === label)?.[2]?.required_value || ''
  const [applicability, setApplicability] = useState(() => Object.fromEntries(
    FIXED_SCORING_CRITERIA.map(([label]) => [
      label,
      existing?.criteria?.find(item => item[0] === label)?.[2]?.is_applicable !== false,
    ]),
  ))
  const today = new Date()
  const todayDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`
  const [f, setF] = useState(() => ({
    title: existing?.title || '',
    cat: existing?.cat || 'Teaching',
    type: existing?.type || 'Full time',
    summary: existing?.summary || '',
    img: existing?.img || 'maths',
    status: existing?.status || 'Draft',
    closing_date: existing?.closing_date && existing.closing_date >= todayDate ? existing.closing_date : '',
    subject: valueFor('teaching subject specialization'),
    qualification: valueFor('academic qualification'),
    experience: valueFor('teaching experience').match(/\d+(?:\.\d+)?/)?.[0] || '',
    skills: valueFor('teaching methodology and classroom management'),
    location: existing?.description?.match(/Location:\s*(.+)/i)?.[1]?.split('\n')[0] || '',
  }))
  const requirementTypes = {
    'academic qualification': ['qualification', f.qualification],
    'teaching subject specialization': ['skill', f.subject],
    'teaching experience': ['experience', `${f.experience || 0} years`],
    'teaching methodology and classroom management': ['keyword', f.skills],
    'professional teaching qualification/training': ['keyword', 'Teacher education or professional teaching training'],
    'additional relevant skills': ['skill', f.skills],
  }
  const cr = FIXED_SCORING_CRITERIA.map(([label, weight]) => [
    label,
    weight,
    {
      criterion_type: requirementTypes[label][0],
      required_value: requirementTypes[label][1],
      is_mandatory: false,
      is_applicable: applicability[label],
    },
  ])
  const total = cr.reduce((sum, criterion) => sum + (criterion[2].is_applicable ? criterion[1] : 0), 0)
  const up = key => event => setF({ ...f, [key]: event.target.value })
  const minClosingDate = todayDate
  const pv = { ...f, id: 0, status: 'Open', closes: '[closing date]', applicants: 0 }
  const save = async status => {
    if (f.closing_date && f.closing_date < minClosingDate) {
      window.alert('Closing date must be today or a future date.')
      return
    }
    const requiredFields = [
      f.title,
      f.location,
      ...(applicability['academic qualification'] ? [f.qualification] : []),
      ...(applicability['teaching subject specialization'] ? [f.subject] : []),
      ...(applicability['teaching experience'] ? [f.experience] : []),
      ...((applicability['teaching methodology and classroom management'] || applicability['additional relevant skills']) ? [f.skills] : []),
    ]
    if (status === 'open' && !cr.some(criterion => criterion[2].is_applicable)) {
      window.alert('Select at least one applicable scoring criterion before publishing.')
      return
    }
    if (status === 'open' && requiredFields.some(value => !String(value).trim())) {
      window.alert('Complete the vacancy details required by the selected scoring criteria before publishing.')
      return
    }
    if (status === 'open' && applicability['teaching experience'] && (!Number.isFinite(Number(f.experience)) || Number(f.experience) < 0 || Number(f.experience) > 60)) {
      window.alert('Teaching experience must be between 0 and 60 years.')
      return
    }
    const description = [
      `Subject: ${f.subject}`,
      `Location: ${f.location}`,
      `Minimum qualification: ${f.qualification}`,
      `Minimum secondary-school teaching experience: ${f.experience || 0} years`,
      `Required skills: ${f.skills}`,
    ].join('\n')
    const payload = { title: f.title, category: f.cat, employment_type: f.type, summary: f.summary, description, image_key: f.img, status, closing_date: f.closing_date || null, criteria: cr.map(c => ({ criterion_type: c[2].criterion_type, label: c[0], required_value: c[2].required_value || c[0], weight: Number(c[1]), is_mandatory: false, is_applicable: c[2].is_applicable })) }
    try { await request(existing ? `/api/vacancies/${existing.id}` : '/api/vacancies', { method: existing ? 'PUT' : 'POST', body: JSON.stringify(payload) }); window.location.href = '/admin/vacancies' } catch (error) { window.alert(error.message) }
  }
  return <><Head title="Vacancy" sub="Define the role details. Screening weights are fixed across all vacancies."><button className="btn g" onClick={() => save('draft')}>Save draft</button><button className="btn" onClick={() => save('open')}>Publish</button></Head>
    <div className="g2" style={{ gridTemplateColumns: '1.5fr 1fr' }}><div className="col" style={{ gap: 22 }}>
      <div className="card col"><h3>Details</h3><Field label="Title" id="t" value={f.title} onChange={up('title')} /><div className="g2"><Select label="Category" id="c" options={['Teaching', 'Non-teaching']} value={f.cat} onChange={up('cat')} /><Select label="Employment type" id="e" options={['Full time', 'Part time', 'Contract']} value={f.type} onChange={up('type')} /></div>
        <div className="g2"><Field label="Subject or specialization" id="subject" required={applicability['teaching subject specialization']} value={f.subject} onChange={up('subject')} /><Field label="Location / district" id="location" required value={f.location} onChange={up('location')} /></div>
        <Field label="Minimum qualification or relevant credential" id="qualification" required={applicability['academic qualification']} value={f.qualification} onChange={up('qualification')} />
        <Field label="Minimum relevant experience (years)" id="experience" type="number" min="0" max="60" step="0.5" required={applicability['teaching experience']} value={f.experience} onChange={up('experience')} />
        <Field label="Required skills or competencies" id="required-skills" as="textarea" rows="3" required={applicability['teaching methodology and classroom management'] || applicability['additional relevant skills']} value={f.skills} onChange={up('skills')} />
        <Field label="Closing date" id="d" type="date" min={minClosingDate} value={f.closing_date || ''} onChange={up('closing_date')} /><Field label="Short summary (shown on the card)" id="s" as="textarea" rows="3" value={f.summary} onChange={up('summary')} />
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}><legend className="fld" style={{ marginBottom: 8 }}>Card picture</legend><div className="pick">{['maths', 'science', 'accounts', 'library', 'english'].map(k => <label key={k}><input type="radio" name="img" checked={f.img === k} onChange={() => setF({ ...f, img: k })} /><img src={`/images/${k}.svg`} alt={k} /></label>)}</div></fieldset></div>
      <div className="card"><div className="row sp"><h3>Fixed scoring criteria</h3><Chip>Applicable weight {total}%</Chip></div>
        <p className="mut">Weights stay fixed. Untick criteria that do not apply to this role; remaining scores are normalized to 100%.</p>
        {cr.map(([label, weight, detail]) => <label className="row sp" key={label} style={{ padding: '12px 0', borderTop: '1px solid #EEF0F5', gap: 12 }}>
          <span className="row" style={{ flex: 1 }}><input type="checkbox" checked={detail.is_applicable} onChange={event => setApplicability(previous => ({ ...previous, [label]: event.target.checked }))} /><span>{label}</span></span><b>{weight}%</b>
        </label>)}</div></div>
      <div className="sticky preview"><p className="mut">Live preview of the public card</p><VCard v={pv} to="/admin/vacancies" /></div></div></>
}

export const Applications = () => {
  const go = useNavigate(); const [anon, setAnon] = useState(false)
  const [{ applications, vacancies }, { advance }] = useStore()
  const vacancy = vacancies.find(v => applications[0] && String(v.id) === String(applications[0].vacancyId))
  const exportReport = format => vacancy && downloadProtected(`/api/reports/${format}?vacancy_id=${vacancy.id}`, `${format}-report`).catch(error => window.alert(error.message))
  // Ranked best-first; unscored (manual check) applications fall to the bottom.
  const rows = [...applications].sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
  return <><Head title={vacancy?.title || 'Applications'} sub={`${rows.length} applicants, ranked by match score`}><LinkBtn to="/admin/compare" k="o">Compare top 3</LinkBtn><button className="btn o" onClick={() => exportReport('csv')} disabled={!vacancy}>Export CSV</button><button className="btn" onClick={() => exportReport('pdf')} disabled={!vacancy}>PDF report</button></Head>
    <div className="card row sp" style={{ flexWrap: 'wrap' }}><div><b>Anonymous review mode</b><br /><span className="mut">Hide names while you review, to reduce unconscious bias.</span></div><input type="checkbox" aria-label="Anonymous review mode" checked={anon} onChange={e => setAnon(e.target.checked)} style={{ width: 24, height: 24, accentColor: '#17305C' }} /></div>
    <div className="card" style={{ padding: 8 }}><Table head={['Rank', 'Applicant', 'Match score', 'Extraction', 'Decision', '']} rows={rows.map((a, i) => [i + 1, <Person n={a.name} hide={anon} />, a.score != null ? <div className="row"><Bar p={a.score} /><b>{a.score}</b></div> : <span className="mut">Not scored</span>, <Chip k={statusKind(a.ext)}>{a.ext === 'Review' ? 'Review extraction' : 'Complete'}</Chip>, <Chip k={a.decision === 'Shortlisted' ? '' : 'n'}>{a.decision}</Chip>, <a href="#" onClick={e => { e.preventDefault(); go('/admin/applications/' + a.id) }}>Review</a>])} /></div>
    <div className="card row sp" style={{ flexWrap: 'wrap' }}><span className="mut">Advance every application that is still in progress</span><button className="btn o sm" onClick={() => applications.filter(a => a.status < 3).forEach(a => advance(a.id))}>Advance pipeline</button></div>
    <p className="mut p0">Scores support the Director’s review. Nothing is hired or rejected automatically.</p></>
}

export function CandidateReview() {
  const { id } = useParams(); const go = useNavigate()
  const [{ applications, vacancies }, { decide, loadApplications }] = useStore()
  const cached = applications.find(x => String(x.id) === String(id))
  const [a, setA] = useState(cached || null)
  const [scoring, setScoring] = useState(false)
  const [scoreError, setScoreError] = useState('')
  useEffect(() => {
    let active = true
    request(`/api/applications/${id}`).then(apiApplication => {
      if (active) setA(apiApplicationToClient(apiApplication))
    }).catch(() => {})
    return () => { active = false }
  }, [id])
  const [d, setD] = useState(cached?.decision === 'Shortlisted' || cached?.decision === 'Hold' || cached?.decision === 'Not shortlisted' ? cached.decision : 'Shortlist')
  const [note, setNote] = useState(a?.note || ''); const [saved, setSaved] = useState(false)

  if (!a) return <><Head title="Application not found" sub="It may have been removed"><LinkBtn to="/admin/applications" k="o">Back to ranking</LinkBtn></Head>
    <div className="card"><p className="mut p0">No application with id {id}. <Link to="/admin/applications">Go back to the ranking</Link>.</p></div></>

  const v = vacancies.find(x => String(x.id) === String(a.vacancyId))
  const cr = v?.criteria || []
  const rank = [...applications].sort((x, y) => (y.score ?? -1) - (x.score ?? -1)).findIndex(x => x.id === a.id) + 1
  const sc = a.scores || cr.map(() => 0)

  const save = () => {
    decide(a.id, d, note).then(() => {
      setSaved(true)
      setTimeout(() => go('/admin/applications'), 700)
    }).catch(() => {})
  }
  const runScoringAgain = async () => {
    if (!window.confirm('Run screening again using the saved applicant profile and current vacancy criteria?')) return
    setScoring(true)
    setScoreError('')
    try {
      const result = await request(`/api/applications/${a.id}/rescore`, { method: 'POST' })
      setA(apiApplicationToClient(result))
      await loadApplications()
    } catch (error) {
      setScoreError(error.message)
    } finally {
      setScoring(false)
    }
  }
  return <><Head title={a.name} sub={`${v?.title || 'Vacancy'} · Rank ${rank} of ${applications.filter(x => x.vacancyId === a.vacancyId).length}`}><button className="btn o" type="button" onClick={runScoringAgain} disabled={scoring}>{scoring ? 'Scoring…' : 'Reset & score again'}</button><LinkBtn to="/admin/applications" k="o">Back to ranking</LinkBtn></Head>
    {scoreError && <p role="alert" className="card" style={{ color: '#9B2C1F' }}>{scoreError}</p>}
    <div className="g2" style={{ gridTemplateColumns: '1.6fr 1fr' }}><div className="col" style={{ gap: 22 }}>
      <div className="card row" style={{ gap: 24 }}>{a.score != null ? <Ring v={a.score} size={110} /> : <span className="mut">Not scored</span>}
        <div><Chip>{scoreBand(a.score)}</Chip><h3 style={{ margin: '8px 0 4px' }}>{a.score != null ? 'Meets the required criteria' : 'Extraction was incomplete'}</h3>
          <span className="mut">{a.ext === 'Review' ? 'The document was scanned, so the extracted text may be unreliable — check the original file.' : 'All documents were read successfully.'}</span></div></div>
      <div className="card"><h3>Applicant details</h3><div className="g2"><p className="mut">Full name<br /><b>{a.name}</b></p><p className="mut">Email<br /><b>{a.email || '—'}</b></p><p className="mut">District<br /><b>{a.district || '—'}</b></p><p className="mut">Phone number<br /><b>{a.phone || '—'}</b></p></div></div>
      <div className="card col"><h3>Why this score</h3>{cr.map((c, i) => { const detail = a.criterionScores?.[i]; const applicable = detail?.is_applicable ?? c[2]?.is_applicable ?? true; const value = Number(detail?.score ?? sc[i] ?? 0); return <div className="col" style={{ gap: 6, opacity: applicable ? 1 : 0.6 }} key={c[0]}><div className="row sp"><b style={{ fontSize: 14 }}>{c[0]}</b><b>{applicable ? `${value} / ${c[1]}` : 'Not applicable'}</b></div>{applicable && <Bar p={c[1] ? Math.round(value / c[1] * 100) : 0} />}<p className="ev">{detail?.evidence || detail?.explanation || 'No matching evidence recorded.'}</p></div> })}</div>
      <div className="card col"><div className="row sp"><h3>Documents</h3>{a.ext === 'Review' && <Chip k="w">OCR confidence lower on this file</Chip>}</div><div className="row" style={{ flexWrap: 'wrap' }}>{a.files.map(f => <button className="btn o sm" key={f}>{f}</button>)}</div>
        <div className="doc" aria-label="Document preview"><i style={{ width: '60%' }} /><i /><i style={{ width: '90%' }} /><i className="hl" style={{ width: '75%' }} /><i /><i style={{ width: '80%' }} /><i className="hl" style={{ width: '55%' }} /><i style={{ width: '70%' }} /></div>
        {a.note && <p className="mut p0">Applicant note: {a.note}</p>}</div></div>
      <form className="card col sticky" onSubmit={e => { e.preventDefault(); save() }}><h3>Your decision</h3>
        {['Shortlist', 'Hold', 'Not shortlisted'].map(o => <label className="opt" key={o}><input type="radio" name="dec" checked={d === o} onChange={() => { setD(o); setSaved(false) }} />{o}</label>)}
        <Field label="Note" id="dn" as="textarea" rows="4" value={note} onChange={e => setNote(e.target.value)} />
        <button className="btn">Record decision</button>
        {saved && <p className="p0" style={{ color: '#176B3A', fontSize: 13.5, fontWeight: 600 }}>Decision recorded in the audit log.</p>}
        {a.decidedBy && !saved && <p className="mut p0">Last recorded by {a.decidedBy}: {a.decision}.</p>}
        <p className="mut p0">The decision and your note are saved to the audit log.</p></form></div></>
}

export function Compare() {
  const [{ applications, vacancies }] = useStore()
  const ranked = [...applications].sort((a, b) => (b.score ?? -1) - (a.score ?? -1))
  const top = ranked.slice(0, 3)
  const cr = vacancies.find(v => String(v.id) === String(top[0]?.vacancyId))?.criteria || []
  return <><Head title="Compare candidates" sub="Top three applicants side by side"><LinkBtn to="/admin/applications" k="o">Back to ranking</LinkBtn></Head>
  {top.length < 2 ? <div className="card"><p className="mut p0">You need at least two applications before you can compare candidates. <Link to="/admin/applications">Back to the ranking</Link>.</p></div> :
    <div className="card"><Table head={['Criterion', ...top.map(a => a.name)]} rows={[...cr.map((c, i) => [<b>{c[0]}<br /><span className="mut">out of {c[1]}</span></b>, ...top.map((a, j) => <div className="row" key={j}><Bar p={Math.round((a.scores?.[i] || 0) / c[1] * 100)} /><b>{a.scores?.[i] ?? 0}</b></div>)]),
      [<b>Total</b>, ...top.map((a, j) => <Ring v={a.score ?? 0} size={72} key={j} />)], ['', ...top.map(a => <Link className="btn sm" to={`/admin/applications/${a.id}`} key={a.id}>Open review</Link>)]]} /></div>}</>
}

export const Users = () => {
  const [{ user, users }, { loadUsers }] = useStore()
  const removeUser = u => {
    if (u.role === 'director') return window.alert('Director accounts cannot be deleted from this page.')
    if (!window.confirm(`Delete account ${u.name || u.full_name} (${u.email})? This cannot be undone.`)) return
    request(`/api/auth/users/${u.id}`, { method: 'DELETE' }).then(() => { window.alert('Account deleted successfully.'); loadUsers() }).catch(error => window.alert(error.message))
  }
  return <><Head title="Users" sub="Manage registered accounts and roles"><button className="btn o" onClick={loadUsers}>Refresh users</button></Head>
  <div className="card" style={{ padding: 8 }}><Table head={['User', 'Email', 'Role', 'Status', 'District', '']} rows={users.map(u => [<Person n={u.name || u.full_name} />, u.email, <Chip k={u.role === 'director' ? 'b' : 'n'}>{u.role === 'director' ? 'Director' : 'Applicant'}</Chip>, <Chip k={u.is_active ? '' : 'w'}>{u.is_active ? 'Active' : 'Disabled'}</Chip>, u.district || '—', u.role === 'director' ? 'Protected' : <button className="btn o sm" onClick={() => removeUser(u)}>Delete</button>])} /></div>
  {users.length === 0 && <p className="mut p0">No registered accounts are available. Refresh after creating an account.</p>}
  {user && <p className="mut p0">You are signed in as <b>{user.name}</b>.</p>}</>
}

export const Categories = () => {
  const [{ vacancies: vs }] = useStore()
  const cats = [...new Set(vs.map(v => v.cat))].map(c => [c, vs.filter(v => v.cat === c).length])
  return <><Head title="Categories" sub="Group vacancies by type" />
  <div className="g2"><div className="card"><Table head={['Category', 'Vacancies', '']} rows={cats.map(([c, n]) => [c, n, <a href="#">Edit</a>])} /></div>
    <form className="card col" onSubmit={e => e.preventDefault()}><h3>Add category</h3><Field label="Name" id="cn" /><Field label="Description" id="cd" as="textarea" rows="3" /><button className="btn" style={{ alignSelf: 'flex-start' }}>Save category</button></form></div></>
}

export const Reports = () => {
  const [{ applications, vacancies }] = useStore()
  const [v, setV] = useState('')
  const [reportError, setReportError] = useState('')
  const selected = vacancies.find(x => x.title === v) || vacancies.find(x => x.status === 'Open')
  const rows = applications.filter(a => String(a.vacancyId) === String(selected?.id))
  const generate = format => {
    if (!selected) return
    setReportError('')
    downloadProtected(`/api/reports/${format}?vacancy_id=${selected.id}`, `${format}-report`).catch(error => setReportError(error.message))
  }
  return <><Head title="Reports" sub="Generate and download recruitment reports" />
  <div style={{ maxWidth: 360 }}><Select label="Vacancy" id="rv" options={vacancies.map(x => x.title)} value={v || selected?.title || ''} onChange={e => setV(e.target.value)} /></div>
  <div className="g3">{[['Ranked shortlist', 'PDF', 'Applicants ranked with scores and evidence'], ['Applicant list', 'CSV', 'All applicants and statuses for a vacancy'], ['Screening summary', 'PDF', 'Counts, extraction warnings and decisions']].map(([t, f, d]) => <div className="card col" key={t}><div className="row sp"><b>{t}</b><Chip>{f}</Chip></div><span className="mut">{d}</span><button className="btn o" type="button" disabled={!selected} onClick={() => generate(f.toLowerCase())}>Generate</button></div>)}</div>
  {reportError && <p className="p0" style={{ color: '#9B2C1F', fontSize: 13.5, fontWeight: 600 }}>{reportError}</p>}
  <div className="card"><h3 style={{ marginBottom: 12 }}>Recent exports</h3><Table head={['Report', 'Vacancy', 'Generated by', 'Date', '']} rows={[['Ranked shortlist', 'Mathematics Teacher', 'Director', '[date]', <a href="#">Download</a>], ['Applicant list', 'English Teacher', 'Director', '[date]', <a href="#">Download</a>]]} /></div>
  <div className="card"><h3 style={{ marginBottom: 12 }}>{v || 'Vacancy'} · {rows.length} application{rows.length === 1 ? '' : 's'}</h3>
    {rows.length === 0 ? <p className="mut p0">No applications for this vacancy yet.</p> : <Table head={['Applicant', 'Match score', 'Decision']} rows={rows.map(a => [<Person n={a.name} />, a.score ?? 'Not scored', <Chip k={a.decision === 'Shortlisted' ? '' : 'n'}>{a.decision}</Chip>])} />}</div></>
}

export const Audit = () => {
  const [{ audit }] = useStore()
  return <><Head title="Audit log" sub="Every screening run and decision is recorded" />
  <div className="card" style={{ padding: 8 }}>{audit.length === 0 ? <p className="mut p0">Nothing has been recorded yet.</p> :
    <Table head={['Who', 'Action', 'Item']} rows={audit.map(a => [<Chip k={a[0] === 'System' ? 'n' : 'b'}>{a[0]}</Chip>, a[1], a[2]])} />}</div></>
}

const Sw = ({ l, d, on = true }) => <div className="sw"><label htmlFor={l}><b>{l}</b><br /><span className="mut">{d}</span></label><input id={l} type="checkbox" defaultChecked={on} /></div>
export const Settings = () => <><Head title="Settings" sub="Screening, security and data retention"><button className="btn">Save settings</button></Head>
  <div className="g2"><div className="card"><h3>Screening</h3><Sw l="OCR for scanned files" d="Use Tesseract when text extraction is insufficient" /><Sw l="Semantic similarity" d="Use Sentence Transformers for related phrases" /><Sw l="Flag low confidence" d="Send low-confidence extractions to manual review" />
    <div className="col" style={{ marginTop: 14 }}><Field label="Minimum extraction confidence (%)" id="mc" defaultValue="60" /><Field label="Maximum upload size (MB)" id="ms" defaultValue="5" /></div></div>
    <div className="col"><div className="card"><h3>Security</h3><Sw l="Require strong passwords" d="Minimum length and mixed characters" /><Field label="Session timeout (minutes)" id="st" defaultValue="30" /></div>
      <div className="card col"><h3>Data retention</h3><Field label="Keep applicant documents for (months)" id="rt" defaultValue="12" /><p className="mut p0">Audit logs record every screening run and decision.</p></div></div></div></>

export const scoreBand = score => {
  if (score == null) return 'Not scored'
  if (score >= 80) return 'Strong match'
  if (score >= 65) return 'Good match'
  if (score >= 50) return 'Partial match'
  return 'Weak match'
}
