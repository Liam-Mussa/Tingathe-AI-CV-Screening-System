import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Chip, Field, Select, Person, Stat, Bar, Table, Head, Ring, VCard, LinkBtn, statusKind } from '../ui.jsx'
import { users, APP_STATUS } from '../data.js'
import { useStore } from '../store.js'
import { downloadProtected, request } from '../api.js'

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

export const Vacancies = () => {
  const [{ vacancies }] = useStore()
  const [tab, setTab] = useState('All'); const rows = vacancies.filter(v => tab === 'All' || v.status === tab)
  return <><Head title="Vacancies" sub="Create, publish and close vacancies"><LinkBtn to="/admin/vacancies/new">New vacancy</LinkBtn></Head>
    <div className="tabs">{['All', 'Open', 'Draft', 'Closed'].map(t => <a key={t} href="#" className={t === tab ? 'on' : ''} onClick={e => { e.preventDefault(); setTab(t) }}>{t}</a>)}</div>
    <div className="vgrid">{rows.map(v => <VCard key={v.id} v={v} admin to={`/admin/vacancies/${v.id}`} />)}<Link to="/admin/vacancies/new" className="vnew">+ New vacancy</Link></div></>
}

export function VacancyBuilder() {
  const [{ vacancies }] = useStore()
  const { id } = useParams()
  const existing = vacancies.find(v => String(v.id) === String(id))
  const [f, setF] = useState(() => ({ title: existing?.title || 'Mathematics Teacher', cat: existing?.cat || 'Teaching', type: existing?.type || 'Full time', summary: existing?.summary || 'Teach Mathematics to Forms 1–4 and support the department.', img: existing?.img || 'maths', status: existing?.status || 'Draft', closing_date: existing?.closing_date || '' }))
  const [cr, setCr] = useState(() => existing?.criteria || [['New criterion', 0, { criterion_type: 'keyword', is_mandatory: false }]]); const total = cr.reduce((s, c) => s + Number(c[1] || 0), 0); const up = k => e => setF({ ...f, [k]: e.target.value })
  const pv = { ...f, id: 0, status: 'Open', closes: '[closing date]', applicants: 0 }
  const save = async status => {
    const payload = { title: f.title, category: f.cat, employment_type: f.type, summary: f.summary, description: f.summary, image_key: f.img, status, closing_date: f.closing_date || null, criteria: cr.map(c => ({ criterion_type: c[2]?.criterion_type || 'keyword', label: c[0], required_value: c[2]?.required_value || c[0], weight: Number(c[1]), is_mandatory: Boolean(c[2]?.is_mandatory) })) }
    try { await request(existing ? `/api/vacancies/${existing.id}` : '/api/vacancies', { method: existing ? 'PUT' : 'POST', body: JSON.stringify(payload) }); window.location.href = '/admin/vacancies' } catch (error) { window.alert(error.message) }
  }
  return <><Head title="Vacancy" sub="Define the role, choose a picture and set the screening criteria"><button className="btn g" onClick={() => save('draft')}>Save draft</button><button className="btn" onClick={() => save('open')}>Publish</button></Head>
    <div className="g2" style={{ gridTemplateColumns: '1.5fr 1fr' }}><div className="col" style={{ gap: 22 }}>
      <div className="card col"><h3>Details</h3><Field label="Title" id="t" value={f.title} onChange={up('title')} /><div className="g2"><Select label="Category" id="c" options={['Teaching', 'Non-teaching']} value={f.cat} onChange={up('cat')} /><Select label="Employment type" id="e" options={['Full time', 'Part time', 'Contract']} value={f.type} onChange={up('type')} /></div>
        <Field label="Closing date" id="d" type="date" value={f.closing_date || ''} onChange={up('closing_date')} /><Field label="Short summary (shown on the card)" id="s" as="textarea" rows="3" value={f.summary} onChange={up('summary')} />
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}><legend className="fld" style={{ marginBottom: 8 }}>Card picture</legend><div className="pick">{['maths', 'science', 'accounts', 'library', 'english'].map(k => <label key={k}><input type="radio" name="img" checked={f.img === k} onChange={() => setF({ ...f, img: k })} /><img src={`/images/${k}.svg`} alt={k} /></label>)}</div>
          <p className="mut">Replace the pictures in <code>public/images</code> with your own school photos.</p></fieldset></div>
      <div className="card"><div className="row sp"><h3>Screening criteria</h3><Chip k={total === 100 ? '' : 'w'}>Total weight {total}</Chip></div>
        {cr.map((c, i) => <div className="row sp" key={i} style={{ padding: '12px 0', borderTop: '1px solid #EEF0F5', flexWrap: 'wrap' }}>
          <div className="col" style={{ flex: 1, minWidth: 220, gap: 8 }}><input aria-label={`Criterion ${i + 1}`} value={c[0]} onChange={e => setCr(cr.map((x, k) => k === i ? [e.target.value, x[1], { ...(x[2] || {}), required_value: e.target.value }] : x))} style={{ width: '100%', font: 'inherit', minHeight: 40, border: '1.5px solid #D5DAE5', borderRadius: 10, padding: '0 10px' }} />
            <div className="row" style={{ flexWrap: 'wrap' }}><select aria-label={`Criterion ${i + 1} type`} value={c[2]?.criterion_type || 'keyword'} onChange={e => setCr(cr.map((x, k) => k === i ? [x[0], x[1], { ...(x[2] || {}), criterion_type: e.target.value }] : x))} style={{ font: 'inherit', minHeight: 36, border: '1.5px solid #D5DAE5', borderRadius: 8, padding: '0 8px' }}><option value="keyword">Keyword</option><option value="qualification">Qualification</option><option value="skill">Skill</option><option value="experience">Experience</option></select><label className="mut"><input type="checkbox" checked={Boolean(c[2]?.is_mandatory)} onChange={e => setCr(cr.map((x, k) => k === i ? [x[0], x[1], { ...(x[2] || {}), is_mandatory: e.target.checked }] : x))} /> Mandatory</label></div></div>
          <div className="row"><label className="mut" htmlFor={'w' + i}>Weight</label><input id={'w' + i} type="number" min="0" max="100" value={c[1]} onChange={e => setCr(cr.map((x, k) => k === i ? [x[0], e.target.value, x[2]] : x))} style={{ width: 70, font: 'inherit', minHeight: 40, border: '1.5px solid #D5DAE5', borderRadius: 10, padding: '0 10px' }} /><a href="#" onClick={e => { e.preventDefault(); setCr(cr.filter((_, k) => k !== i)) }}>Remove</a></div></div>)}
        <button className="btn o" style={{ marginTop: 14 }} onClick={() => setCr([...cr, ['New criterion', 0, { criterion_type: 'keyword', is_mandatory: false }]])}>Add criterion</button></div></div>
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
  const [{ applications, vacancies }, { decide }] = useStore()
  const a = applications.find(x => String(x.id) === String(id))
  const [d, setD] = useState(a?.decision === 'Shortlisted' || a?.decision === 'Hold' || a?.decision === 'Not shortlisted' ? a.decision : 'Shortlist')
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
  return <><Head title={a.name} sub={`${v?.title || 'Vacancy'} · Rank ${rank} of ${applications.filter(x => x.vacancyId === a.vacancyId).length}`}><LinkBtn to="/admin/applications" k="o">Back to ranking</LinkBtn></Head>
    <div className="g2" style={{ gridTemplateColumns: '1.6fr 1fr' }}><div className="col" style={{ gap: 22 }}>
      <div className="card row" style={{ gap: 24 }}>{a.score != null ? <Ring v={a.score} size={110} /> : <span className="mut">Not scored</span>}
        <div><Chip>{a.score != null ? 'Strong match' : 'Needs manual check'}</Chip><h3 style={{ margin: '8px 0 4px' }}>{a.score != null ? 'Meets the required criteria' : 'Extraction was incomplete'}</h3>
          <span className="mut">{a.ext === 'Review' ? 'The document was scanned, so the extracted text may be unreliable — check the original file.' : 'All documents were read successfully.'}</span></div></div>
      <div className="card col"><h3>Why this score</h3>{cr.map((c, i) => { const detail = a.criterionScores?.[i]; const value = Number(detail?.score ?? sc[i] ?? 0); return <div className="col" style={{ gap: 6 }} key={c[0]}><div className="row sp"><b style={{ fontSize: 14 }}>{c[0]}</b><b>{value} / {c[1]}</b></div><Bar p={c[1] ? Math.round(value / c[1] * 100) : 0} /><p className="ev">{detail?.evidence || detail?.explanation || 'No matching evidence recorded.'}</p></div> })}</div>
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
  const [{ user }, { signIn }] = useStore()
  return <><Head title="Users" sub="Manage accounts and roles"><button className="btn" onClick={() => signIn({ email: 'william@example.com', password: 'director123' })}>Sign in as Director</button></Head>
  <div className="card" style={{ padding: 8 }}><Table head={['User', 'Email', 'Role', 'Status', '']} rows={users.map(u => [<Person n={u[0]} />, u[1], <Chip k={u[2] === 'Director' ? 'b' : 'n'}>{u[2]}</Chip>, <Chip k={statusKind(u[3])}>{u[3]}</Chip>, <><a href="#">Edit</a> · <a href="#">Reset password</a></>])} /></div>
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
