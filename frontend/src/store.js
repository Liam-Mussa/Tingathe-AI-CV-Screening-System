// Shared client state backed by the FastAPI service.
// Pages keep the same [state, actions] interface while persistence and
// screening now happen on the server.
import { useCallback, useEffect, useMemo, useState } from 'react'
import { request, setToken, getToken, apiApplicationToClient, apiVacancyToClient } from './api.js'

const KEY = 'tingathe.state.v2'
const listeners = new Set()
let bootstrapStarted = false
let state = loadState()

function loadState() {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) return { user: null, vacancies: [], applications: [], audit: [], loading: false, error: '', ...JSON.parse(raw) }
  } catch { /* start clean if storage is unavailable or corrupt */ }
  return { user: null, vacancies: [], applications: [], audit: [], loading: false, error: '' }
}

function persist(next) {
  state = { ...state, ...next }
  try { localStorage.setItem(KEY, JSON.stringify(state)) } catch { /* storage may be unavailable */ }
  listeners.forEach(listener => listener(state))
  return state
}

function replaceUser(user, token) {
  setToken(token)
  return persist({ user: user ? { ...user, name: user.name || user.full_name } : null, error: '' })
}

async function refreshVacancies() {
  const data = await request('/api/vacancies')
  const vacancies = data.map(apiVacancyToClient)
  persist({ vacancies, error: '' })
  return vacancies
}

async function refreshApplications() {
  const data = await request('/api/applications')
  const applications = data.map(apiApplicationToClient)
  persist({ applications, error: '' })
  return applications
}

async function refreshAudit() {
  if (!state.user || state.user.role !== 'director') return []
  const data = await request('/api/audit')
  const audit = data.map(row => row.row?.length ? row.row : [row.actor, row.action, row.item || ''])
  persist({ audit, error: '' })
  return audit
}

function capture(error) {
  const message = error?.message || 'Something went wrong. Please try again.'
  persist({ error: message, loading: false })
  return null
}

const actions = {
  async bootstrap() {
    persist({ loading: true, error: '' })
    try {
      await refreshVacancies()
      if (getToken()) {
        const me = await request('/api/auth/me')
        replaceUser(me, getToken())
        await refreshApplications()
        await refreshAudit()
      }
      persist({ loading: false })
    } catch (error) {
      if (error.status === 401) {
        setToken(null)
        persist({ user: null, applications: [], audit: [] })
      }
      capture(error)
    }
  },

  async signIn(credentials) {
    persist({ loading: true, error: '' })
    try {
      const result = await request('/api/auth/login', { method: 'POST', body: JSON.stringify(credentials) })
      replaceUser(result.user, result.access_token)
      await refreshApplications()
      await refreshAudit()
      persist({ loading: false })
      return result.user
    } catch (error) { capture(error); throw error }
  },

  async register(details) {
    persist({ loading: true, error: '' })
    try {
      const result = await request('/api/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          full_name: details.name,
          email: details.email,
          password: details.password,
          phone: details.phone || null,
          district: details.district || null,
          consent: true,
        }),
      })
      replaceUser(result.user, result.access_token)
      persist({ applications: [], loading: false })
      return result.user
    } catch (error) { capture(error); throw error }
  },

  async signOut() {
    setToken(null)
    persist({ user: null, applications: [], audit: [], error: '' })
  },

  async loadVacancies() {
    try { return await refreshVacancies() } catch (error) { capture(error); return [] }
  },

  async loadApplications() {
    try { return await refreshApplications() } catch (error) { capture(error); return [] }
  },

  async apply({ vacancyId, phone, note, files }) {
    persist({ loading: true, error: '' })
    try {
      const form = new FormData()
      form.append('vacancy_id', String(vacancyId))
      form.append('phone', phone || '')
      form.append('note', note || '')
      for (const file of files || []) {
        if (file instanceof File) form.append('files', file, file.name)
      }
      const result = await request('/api/applications', { method: 'POST', body: form })
      const application = apiApplicationToClient(result)
      persist({ applications: [application, ...state.applications.filter(item => item.id !== application.id)], loading: false, error: '' })
      return application
    } catch (error) { capture(error); throw error }
  },

  async decide(id, decision, note) {
    persist({ loading: true, error: '' })
    try {
      const apiDecision = { Shortlist: 'shortlist', Hold: 'hold', 'Not shortlisted': 'not_shortlisted' }[decision] || decision
      const result = await request(`/api/applications/${id}/decision`, {
        method: 'POST',
        body: JSON.stringify({ decision: apiDecision, note: note || null }),
      })
      const application = apiApplicationToClient(result)
      persist({ applications: state.applications.map(item => item.id === application.id ? application : item), loading: false, error: '' })
      await refreshAudit()
      return application
    } catch (error) { capture(error); throw error }
  },

  async advance(id) {
    try {
      const result = await request(`/api/applications/${id}/advance`, { method: 'POST' })
      const application = apiApplicationToClient(result)
      persist({ applications: state.applications.map(item => item.id === application.id ? application : item), error: '' })
      return application
    } catch (error) { capture(error); throw error }
  },
}

export function useStore() {
  const [snap, setSnap] = useState(state)
  useEffect(() => {
    listeners.add(setSnap)
    if (!bootstrapStarted) {
      bootstrapStarted = true
      actions.bootstrap()
    }
    return () => listeners.delete(setSnap)
  }, [])
  return [snap, useMemo(() => actions, [])]
}

export function useRanked(vacancyId) {
  const [snap] = useStore()
  return useCallback(
    () => snap.applications.filter(application => String(application.vacancyId) === String(vacancyId)).sort((a, b) => (b.score ?? -1) - (a.score ?? -1)),
    [snap.applications, vacancyId],
  )()
}
