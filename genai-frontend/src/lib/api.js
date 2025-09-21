import { auth } from './firebase.js'

const BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')
const LOGIN_PATH = import.meta.env.VITE_API_LOGIN_PATH || '/login'
const CHAT_PATH = import.meta.env.VITE_API_CHAT_PATH || '/dialogflow-webhook'
const CONSENT_PATH = import.meta.env.VITE_API_CONSENT_PATH || '/consent'

async function http(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
    ...opts,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.headers.get('content-type')?.includes('application/json') ? res.json() : res.text()
}

export const api = {
  // Login: send Firebase ID token in Authorization like authchat.py
  login: async (token) => {
    if (!token) throw new Error('No token')
    return http(LOGIN_PATH, { method: 'POST', headers: { Authorization: `Bearer ${token}` } })
  },

  // Consent: POST /consent with { consent } like authchat.py set_consent
  async consent({ consent }) {
    const t = await auth.currentUser?.getIdToken(true)
    return http(CONSENT_PATH, {
      method: 'POST',
      headers: { Authorization: `Bearer ${t}` },
      body: JSON.stringify({ consent }),
    })
  },

  // lib/api.js
async sendMessage({ session, message }) {
  const t = await auth.currentUser?.getIdToken(true)
  const body = {
    session,
    messages: [{ text: { text: [message] } }],
  }
  return http(import.meta.env.VITE_API_CHAT_PATH || '/dialogflow-webhook', {
    method: 'POST',
    headers: { Authorization: `Bearer ${t}` },
    body: JSON.stringify(body),
  })
},
}


