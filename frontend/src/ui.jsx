import { useState } from 'react'
import { NavLink, Outlet, Link, Navigate } from 'react-router-dom'
import { ADMIN_NAV } from './data.js'
import { useStore } from './store.js'
import { getToken } from './api.js'
const I = {
 grid:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
 briefcase:'<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2"/>',
 files:'<path d="M7 3h7l4 4v14H7z"/><path d="M14 3v4h4"/>',
 users:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.5 3-6 6.5-6s6.5 2.5 6.5 6"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5c2 .8 3.5 2.7 3.5 5.5"/>',
 tag:'<path d="M3 12V4h8l10 10-8 8z"/><circle cx="7.5" cy="8.5" r="1.2"/>',
 chart:'<path d="M4 20V4M4 20h16"/><path d="M8 16v-5M13 16V8M18 16v-3"/>',
 gear:'<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2M19 5l-2 2M7 17l-2 2"/>',
 shield:'<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M9 12l2 2 4-4"/>',
 bell:'<path d="M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 21h4"/>',
 upload:'<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v4h16v-4"/>' }
export const Icon = ({ n }) => <svg className="ic" viewBox="0 0 24 24" aria-hidden="true" dangerouslySetInnerHTML={{ __html: I[n] }} />
export const statusKind = s => ({ Open: '', Draft: 'n', Closed: 'r', Active: '', Disabled: 'r', Complete: '', Review: 'w' }[s] ?? 'n')
export const Chip = ({ k = '', children }) => <span className={`chip ${k}`}>{children}</span>
export const Av = ({ n }) => <span className="av" aria-hidden="true">{n.split(' ').slice(0, 2).map(x => x[0]).join('')}</span>
export const Person = ({ n, s, hide }) => <div className="row" style={{ gap: 10 }}>{hide ? <span className="av">?</span> : <Av n={n} />}<div><b>{hide ? 'Anonymous applicant' : n}</b>{s && <><br /><span className="mut">{s}</span></>}</div></div>
export const Stat = ({ l, v, n, i }) => <div className="card stat"><span className="ico"><Icon n={i} /></span><div><p className="mut p0">{l}</p><h2>{v}</h2><span className="mut">{n}</span></div></div>
export const Bar = ({ p }) => <div className="bar"><i style={{ width: p + '%' }} /></div>
export const Table = ({ head, rows }) => <div className="tw"><table><thead><tr>{head.map(h => <th key={h}>{h}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={i}>{r.map((c, j) => <td key={j}>{c}</td>)}</tr>)}</tbody></table></div>
export const Field = ({ label, id, as: T = 'input', children, ...p }) => <div className="fld"><label htmlFor={id}>{label}</label><T id={id} {...p}>{children}</T></div>
export const Select = ({ label, id, options, ...p }) => <Field label={label} id={id} as="select" {...p}>{options.map(o => <option key={o}>{o}</option>)}</Field>
export const Head = ({ title, sub, children }) => <div className="bar2"><div><h1>{title}</h1><p className="mut p0">{sub}</p></div><div className="row">{children}</div></div>
export const LinkBtn = ({ to, k = '', children }) => <Link to={to} className={`btn ${k}`}>{children}</Link>
export function Ring({ v, size = 96 }) {
  const r = 40, c = 2 * Math.PI * r
  return <svg width={size} height={size} viewBox="0 0 100 100" role="img" aria-label={`Score ${v} out of 100`}><circle cx="50" cy="50" r={r} fill="none" stroke="#E4E7EE" strokeWidth="9" /><circle cx="50" cy="50" r={r} fill="none" stroke="#17305C" strokeWidth="9" strokeLinecap="round" strokeDasharray={`${c * v / 100} ${c}`} transform="rotate(-90 50 50)" /><text x="50" y="58" textAnchor="middle" fontSize="28" fontWeight="800" fill="#101828">{v}</text></svg>
}
export const VCard = ({ v, to, admin }) => <Link to={to} className="vcard"><div className="vimg"><img src={`/images/${v.img}.svg`} alt="" /><Chip k={statusKind(v.status)}>{v.status}</Chip></div>
  <div className="vbody"><span className="mut">{v.cat} · {v.type}</span><h3>{v.title}</h3><p className="mut">{v.summary}</p>
    <div className="row sp"><span className="mut">{admin ? `${v.applicants} applicants` : `Closes ${v.closes}`}</span><span className="arrow">{admin ? 'Manage' : 'View and apply'} →</span></div></div></Link>
export function Dropzone({ label, hint, multiple, onFiles }) {
  const [f, setF] = useState([])
  const pick = e => { const files = [...e.target.files]; setF(files.map(x => x.name)); onFiles && onFiles(files) }
  return <div className="fld"><span>{label}</span><label className="drop"><Icon n="upload" /><b>Choose files or drop them here</b><small>{hint}</small>
    <input type="file" multiple={multiple} accept=".pdf,.doc,.docx,.png,.jpg,.jpeg" onChange={pick} /></label>{f.length > 0 && <div className="row" style={{ flexWrap: 'wrap', gap: 6 }}>{f.map(n => <Chip key={n} k="b">{n}</Chip>)}</div>}</div>
}
export const Brand = ({ light, sub = 'Careers' }) => <Link to="/" className={`brandlk ${light ? 'light' : ''}`}><span className="crest">T</span><span><b>Tingathe Secondary School</b><br /><small>{sub}</small></span></Link>
export function PublicLayout() {
  const [{ user }, { signOut }] = useStore()
  return <><header className="pub-nav"><Brand /><nav aria-label="Main"><NavLink to="/" end>Vacancies</NavLink><NavLink to="/me">My applications</NavLink></nav>
    <div className="row" style={{ gap: 8 }}>{user
      ? <><span className="mut" style={{ fontSize: 13.5 }}>{user.name}</span><button className="btn o sm" onClick={signOut}>Sign out</button></>
      : <><Link to="/login" className="btn o sm">Sign in</Link><Link to="/register" className="btn sm">Create account</Link></>}</div></header>
    <Outlet /><footer className="foot">Tingathe Secondary School recruitment. Applications are screened with software support; every final decision is made by the Director.</footer></>
}
export function AdminLayout() {
  const [lang, setLang] = useState('English'); const [{ user }, { signOut }] = useStore()
  if (!user && getToken()) return <div className="authr"><p className="mut">Loading your Director workspace…</p></div>
  if (!user || user.role !== 'director') return <Navigate to="/login" replace />
  return <div className="app"><nav className="sb" aria-label="Main"><Brand sub="Recruitment" />
    {ADMIN_NAV.map(([to, l, ic, end]) => <NavLink key={to} to={to} end={end} className="nv"><Icon n={ic} />{l}</NavLink>)}
    <div className="me"><Av n={user?.name || 'Director'} /><span>{user?.role === 'director' ? 'Director' : 'Guest'}<br /><Link to="/login" onClick={signOut}>Sign out</Link></span></div></nav>
    <main className="mn"><div className="top"><input className="search" aria-label="Search" placeholder="Search applicants, vacancies" />
      <div className="row"><select aria-label="Language" value={lang} onChange={e => setLang(e.target.value)}><option>English</option><option>Chichewa</option></select><span className="bell" role="img" aria-label="Notifications"><Icon n="bell" /><i /></span></div></div><Outlet /></main></div>
}
