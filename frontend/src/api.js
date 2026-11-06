const TOKEN_KEY = 'tingathe.access_token'

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) } catch { return null }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* storage may be unavailable */ }
}

export async function request(path, options = {}) {
  const headers = new Headers(options.headers || {})
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(path, { ...options, headers })
  const contentType = response.headers.get('content-type') || ''
  const body = contentType.includes('application/json') ? await response.json() : await response.text()
  if (!response.ok) {
    const message = typeof body === 'object' && body?.detail ? body.detail : `Request failed (${response.status})`
    const error = new Error(message)
    error.status = response.status
    throw error
  }
  return body
}

export async function downloadProtected(path, fallbackName = 'download') {
  const headers = new Headers()
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const response = await fetch(path, { headers })
  if (!response.ok) {
    const contentType = response.headers.get('content-type') || ''
    const body = contentType.includes('application/json') ? await response.json() : await response.text()
    const message = typeof body === 'object' && body?.detail ? body.detail : `Download failed (${response.status})`
    const error = new Error(message)
    error.status = response.status
    throw error
  }

  const blob = await response.blob()
  const disposition = response.headers.get('content-disposition') || ''
  const filename = disposition.match(/filename="?([^";]+)"?/i)?.[1] || fallbackName
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

export function apiVacancyToClient(v) {
  const criteria = (v.criteria || []).map(c => [c.label, Number(c.weight || 0), c])
  return {
    ...v,
    id: v.id,
    cat: v.cat || v.category || 'General',
    type: v.type || v.employment_type || '',
    img: v.img || v.image_key || 'maths',
    closes: v.closes || (v.closing_date ? new Date(`${v.closing_date}T00:00:00`).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'),
    applicants: v.applicants || 0,
    status: v.status ? v.status[0].toUpperCase() + v.status.slice(1) : 'Draft',
    criteria,
  }
}

const STATUS_LABELS = ['Received', 'Processing', 'Under review', 'Decision']

export function apiApplicationToClient(a) {
  const decision = a.decision || 'Undecided'
  return {
    ...a,
    id: a.id,
    vacancyId: a.vacancyId || a.vacancy_id,
    name: a.name || 'Applicant',
    files: a.files || [],
    ext: a.ext || a.extraction_status || 'Complete',
    score: a.score == null ? null : Number(a.score),
    status: Number.isInteger(a.status) ? a.status : 0,
    statusLabel: a.status_label || STATUS_LABELS[a.status] || 'Received',
    decision,
    decidedBy: a.decidedBy || a.decided_by || null,
    createdAt: a.createdAt || a.created_at?.slice?.(0, 10) || '',
    scores: a.scores?.map(Number) || null,
    criterionScores: a.criterion_scores || [],
    warnings: a.warnings || [],
  }
}
