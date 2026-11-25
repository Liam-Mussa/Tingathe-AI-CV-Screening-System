import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { Chip, Field, PasswordField, Bar, VCard, Dropzone, Brand } from '../ui.jsx'
import { APP_STATUS } from '../data.js'
import { useStore } from '../store.js'

export function Landing() {
  const [{ vacancies }] = useStore()
  const open = vacancies.filter(v => v.status === 'Open')
  return <>
    <section className="hero"><div><span className="eyebrow">Now hiring</span><h1>Teach, lead and grow at Tingathe Secondary School.</h1>
      <p>Apply online in minutes, from your phone or computer. Your documents help our Director compare applications fairly, and a person makes every final decision.</p>
      <div className="row" style={{ marginTop: 24, flexWrap: 'wrap' }}><a href="#vacancies" className="btn gold">See open vacancies</a><Link to="/register" className="btn ghost">Create account</Link></div></div>
      <img src="/images/hero.svg" alt="Illustration of Tingathe Secondary School" /></section>
    <div className="strip"><div>{open.length} open vacancies</div><div>PDF, Word and scanned files <span>accepted</span></div><div>Track your application <span>online</span></div><div>Final decision by <span>a person</span></div></div>
    <section className="sec" id="vacancies"><h2>Open vacancies</h2><p className="mut">Choose a role to read the requirements and apply.</p>
      <div className="vgrid">{open.map(v => <VCard key={v.id} v={v} to={`/vacancies/${v.id}`} />)}</div></section>
    <section className="sec alt"><h2>How applying works</h2><p className="mut">Three steps, and you can follow progress at any time.</p>
      <div className="g3">{[['Create your account', 'Register once with your email and phone number.'], ['Upload your documents', 'Add your CV and certificates. Scans and photos are fine.'], ['Follow your progress', 'See when your application is received, reviewed and decided.']].map(([t, d], i) =>
        <div className="step" key={t}><b className="n">{i + 1}</b><div><h3>{t}</h3><p className="mut">{d}</p></div></div>)}</div></section>
    <section className="sec"><div className="card promise"><h2 style={{ fontSize: 22 }}>Our fairness promise</h2><p className="mut p0">Software highlights how your documents match the role. It never hires or rejects anyone. The Director reviews each application and records the decision.</p></div></section></>
}

export function VacancyDetail() {
  const { id } = useParams(); const go = useNavigate()
  const [{ user, vacancies }, { apply }] = useStore()
  const v = vacancies.find(x => String(x.id) === id) || vacancies[0]
  const [step, setStep] = useState(0); const steps = ['Documents', 'Details', 'Review']
  const [files, setFiles] = useState([]); const [phone, setPhone] = useState(user?.phone || ''); const [note, setNote] = useState('')
  const [consent, setConsent] = useState(false); const [err, setErr] = useState('')
  if (!v) return <section className="sec"><div className="card"><p className="mut p0">Loading vacancy…</p></div></section>
  const closed = v.status === 'Closed'

  // Applicants must be signed in to apply; the form collects what we need.
  const next = () => {
    if (step === 0 && files.length === 0) return setErr('Please upload your CV to continue.')
    if (step === 1 && phone.trim().length < 6) return setErr('Please enter a phone number we can reach you on.')
    setErr(''); setStep(step + 1)
  }
  const submit = () => {
    if (!consent) return setErr('Please agree to your documents being processed before applying.')
    if (!user) { go('/login'); return }
    apply({ vacancyId: v.id, phone, note, files }).then(() => go('/me')).catch(error => setErr(error.message))
  }
  const onFiles = list => {
    setFiles(previous => {
      const combined = [...previous, ...list]
      return combined.filter((file, index, all) => all.findIndex(item => item.name === file.name) === index)
    })
    setErr('')
  }

  return <>
    <section className="banner" style={{ backgroundImage: `linear-gradient(90deg,rgba(23,48,92,.94),rgba(23,48,92,.5)),url(/images/${v.img}.svg)` }}>
      <Link to="/" className="back">← All vacancies</Link><span className="eyebrow">{v.cat} · {v.type}</span><h1>{v.title}</h1><p>Closes {v.closes}</p></section>
    <div className="sec two"><div className="col" style={{ gap: 22 }}>
      <div className="card"><h3>About the role</h3><p className="mut" style={{ fontSize: 15 }}>{v.summary} [Full role description from the Director appears here.]</p></div>
      <div className="card"><h3>What we are looking for</h3><ul className="chk">{v.criteria.map(c => <li key={c[0]}>{c[0]}</li>)}</ul></div></div>
    <aside className="card col apply"><h3>Apply for this role</h3>
      <ol className="stepper">{steps.map((s, i) => <li key={s} className={i === step ? 'on' : i < step ? 'done' : ''}>{i + 1}. {s}</li>)}</ol>
      {closed && <p className="mut p0">This vacancy has closed. You can still sign in to see the vacancies that are open.</p>}
      {!closed && step === 0 && <><Dropzone label="CV (PDF or Word)" hint="Max 5 MB" onFiles={onFiles} /><Dropzone label="Certificates and qualifications" hint="Scans and photos accepted" multiple onFiles={onFiles} /></>}
      {!closed && step === 1 && <><Field label="Phone number" id="ph" type="tel" value={phone} onChange={e => { setPhone(e.target.value); setErr('') }} /><Field label="Cover note (optional)" id="cn" as="textarea" rows="4" value={note} onChange={e => setNote(e.target.value)} /></>}
      {!closed && step === 2 && <><p className="mut p0">Applying for <b>{v.title}</b>. Software reads your documents to help the Director compare applications. The Director makes the final decision.</p>
        {files.length > 0 && <div className="row" style={{ flexWrap: 'wrap', gap: 6 }}>{files.map(file => <Chip key={file.name} k="b">{file.name}</Chip>)}</div>}
        <label className="row" style={{ alignItems: 'flex-start', fontSize: 13.5 }}><input type="checkbox" checked={consent} onChange={e => { setConsent(e.target.checked); setErr('') }} style={{ width: 20, height: 20, accentColor: '#17305C' }} /> I agree to my documents being processed for this recruitment.</label></>}
      {err && <p className="p0" style={{ color: '#9B2C1F', fontSize: 13.5, fontWeight: 600 }}>{err}</p>}
      {!closed && <div className="row sp">{step > 0 ? <button className="btn g" onClick={() => { setErr(''); setStep(step - 1) }}>Back</button> : <span />}
        {step < 2 ? <button className="btn" onClick={next}>Continue</button> : <button className="btn gold" onClick={submit}>{user ? 'Submit application' : 'Sign in to submit'}</button>}</div>}</aside></div></>
}

const ST = APP_STATUS
export function MyApplications() {
  const [{ user, applications, vacancies }, { loadApplications }] = useStore()
  const mine = user ? applications : []
  return <section className="sec"><h1>My applications</h1><p className="mut">Follow where each application is. Scores are never shown to applicants.</p>
    {!user && <div className="card col" style={{ maxWidth: 520 }}><h3>You are not signed in</h3><p className="mut p0">Sign in to see the status of your applications, or create an account to apply.</p>
      <div className="row"><Link to="/login" className="btn">Sign in</Link><Link to="/register" className="btn o">Create account</Link></div></div>}
    {user && <div className="row sp" style={{ flexWrap: 'wrap' }}><span className="mut">Signed in as <b>{user.name}</b></span><div className="row"><button className="btn o sm" onClick={loadApplications}>Refresh</button></div></div>}
    <div className="col" style={{ gap: 20 }}>{mine.map(a => { const v = vacancies.find(x => String(x.id) === String(a.vacancyId)); return <div className="card col" key={a.id}>
      <div className="row"><img src={`/images/${v.img}.svg`} alt="" style={{ width: 96, height: 64, borderRadius: 12, objectFit: 'cover' }} /><div style={{ flex: 1 }}><h3>{v.title}</h3><span className="mut">Applied {a.createdAt} · {a.files.length} document{a.files.length === 1 ? '' : 's'}</span></div><Chip k="b">{ST[a.status]}</Chip></div>
      <div className="row" style={{ gap: 6 }}>{ST.map((x, k) => <Bar key={x} p={k <= a.status ? 100 : 0} />)}</div><div className="row sp mut">{ST.map(x => <span key={x}>{x}</span>)}</div>
      {a.decision === 'Shortlisted' && <Chip>Shortlisted for interview</Chip>}</div> })}</div>
    {user && mine.length === 0 && <div className="card col"><h3>No applications yet</h3><p className="mut p0">Browse the open vacancies and apply — it takes a few minutes.</p><Link to="/" className="btn" style={{ alignSelf: 'flex-start' }}>See open vacancies</Link></div>}</section>
}

const Side = ({ h, p }) => <div className="authl"><Brand light /><div><h1>{h}</h1><p>{p}</p></div><img src="/images/hero.svg" alt="" /></div>
const Tabs = ({ on }) => <div className="tabs"><Link to="/login" className={on === 0 ? 'on' : ''}>Sign in</Link><Link to="/register" className={on === 1 ? 'on' : ''}>Create account</Link></div>

export function Login() {
  const go = useNavigate(); const [{ loading }, { signIn }] = useStore()
  const [f, setF] = useState({ email: '', password: '' }); const [localError, setLocalError] = useState('')
  const up = k => e => setF({ ...f, [k]: e.target.value })
  const submit = e => {
    e.preventDefault(); setLocalError('')
    if (!/^\S+@\S+\.\S+$/.test(f.email)) return setLocalError('Enter a valid email address.')
    if (!f.password) return setLocalError('Enter your password.')
    signIn({ email: f.email, password: f.password }).then(user => {
      window.alert('Login successful. Welcome back!')
      go(user.role === 'director' ? '/admin' : '/me')
    }).catch(error => setLocalError(error.message || 'Invalid email or password. Please try again.'))
  }
  return <div className="auth"><Side h="Welcome back." p="Sign in to apply for vacancies or review applications." />
    <div className="authr"><form className="card col" style={{ width: 400 }} onSubmit={submit}><Tabs on={0} /><h1 style={{ fontSize: 26 }}>Sign in</h1>
      <Field label="Email" id="e" type="email" required value={f.email} onChange={up('email')} /><PasswordField label="Password" id="p" required value={f.password} onChange={up('password')} />
      <div className="row sp"><span /><Link to="/forgot-password">Forgot password?</Link></div>
      <button className="btn" type="submit" disabled={loading}>Sign in</button>
      {localError && <p className="p0" style={{ color: '#9B2C1F', fontSize: 13.5, fontWeight: 600 }}>{localError}</p>}
    </form></div></div>
}
export function Register() {
  const go = useNavigate(); const [{ loading }, { register }] = useStore()
  const [f, setF] = useState({ name: '', email: '', phone: '', district: '', password: '', passwordConfirmation: '' }); const [ok, setOk] = useState(false)
  const [localError, setLocalError] = useState('')
  const up = k => e => setF({ ...f, [k]: e.target.value })
  const submit = e => {
    e.preventDefault(); setLocalError('')
    if (!f.name.trim() || !/^\S+@\S+\.\S+$/.test(f.email)) return setLocalError('Enter your name and a valid email address.')
    if (f.password.length < 8 || !/[A-Z]/.test(f.password) || !/[0-9]/.test(f.password)) return setLocalError('Password must have at least 8 characters, one uppercase letter and one number.')
    if (f.password !== f.passwordConfirmation) return setLocalError('Password confirmation does not match.')
    if (!ok) return setLocalError('You must agree to recruitment document processing.')
    register(f).then(() => { window.alert('Your account has been created successfully.'); go('/me') }).catch(error => setLocalError(error.message || 'Registration failed.'))
  }
  return <div className="auth"><Side h="Start your application." p="Create an account once, then apply to any open vacancy." />
    <div className="authr"><form className="card col" style={{ width: 420 }} onSubmit={submit}><Tabs on={1} />
      <Field label="Full name" id="a" required value={f.name} onChange={up('name')} /><Field label="Email" id="b" type="email" required value={f.email} onChange={up('email')} />
      <Field label="Phone" id="c" type="tel" value={f.phone} onChange={up('phone')} /><Field label="District" id="d" value={f.district} onChange={up('district')} />
      <PasswordField label="Password" id="f" required value={f.password} onChange={up('password')} /><PasswordField label="Confirm password" id="fc" required value={f.passwordConfirmation} onChange={up('passwordConfirmation')} />
      <label className="row" style={{ fontSize: 13.5, alignItems: 'flex-start' }}><input type="checkbox" checked={ok} onChange={e => setOk(e.target.checked)} /> I agree to my documents being processed for recruitment screening.</label>
      <button className="btn" type="submit" disabled={loading}>Create account</button>
      {localError && <p className="p0" style={{ color: '#9B2C1F', fontSize: 13.5, fontWeight: 600 }}>{localError}</p>}
    </form></div></div>
  }
  export function ForgotPassword() {
    const [{ loading }, { forgotPassword }] = useStore(); const [email, setEmail] = useState(''); const [message, setMessage] = useState(''); const [error, setError] = useState(''); const [token, setToken] = useState('')
    const submit = e => { e.preventDefault(); setError(''); setMessage(''); forgotPassword(email).then(result => { setToken(result.reset_token || ''); setMessage(result.message) }).catch(err => setError(err.message)) }
    return <div className="auth"><Side h="Recover your account." p="Request a secure password reset link." /><div className="authr"><form className="card col" style={{ width: 420 }} onSubmit={submit}><Tabs on={0} /><h1 style={{ fontSize: 26 }}>Forgot password</h1><Field label="Registered email" id="reset-email" type="email" required value={email} onChange={e => setEmail(e.target.value)} /><button className="btn" disabled={loading}>Request reset</button>{token && <><p className="mut p0">Development reset token:</p><code style={{ overflowWrap: 'anywhere' }}>{token}</code><Link className="btn o" to={`/reset-password/${token}`}>Continue to reset</Link></>}{message && <p style={{ color: '#176B3A' }}>{message}</p>}{error && <p style={{ color: '#9B2C1F' }}>{error}</p>}</form></div></div>
  }
  
  export function ResetPassword() {
    const { token } = useParams(); const go = useNavigate(); const [{ loading }, { resetPassword }] = useStore(); const [password, setPassword] = useState(''); const [confirmation, setConfirmation] = useState(''); const [error, setError] = useState('')
    const submit = e => { e.preventEvent?.(); e.preventDefault(); setError(''); if (password !== confirmation) return setError('Password confirmation does not match.'); resetPassword(token, password, confirmation).then(() => { window.alert('Password reset successfully'); go('/login') }).catch(err => setError(err.message)) }
    return <div className="auth"><Side h="Choose a new password." p="Use a strong password you have not used before." /><div className="authr"><form className="card col" style={{ width: 420 }} onSubmit={submit}><h1 style={{ fontSize: 26 }}>Reset password</h1><PasswordField label="New password" id="new-password" required value={password} onChange={e => setPassword(e.target.value)} /><PasswordField label="Confirm password" id="confirm-password" required value={confirmation} onChange={e => setConfirmation(e.target.value)} /><button className="btn" disabled={loading}>Set new password</button>{error && <p style={{ color: '#9B2C1F' }}>{error}</p>}</form></div></div>
  }
