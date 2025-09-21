const BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')
import { getAuth } from 'firebase/auth'

async function http(path, opts = {}) {
  const auth = getAuth()
  const user = auth.currentUser
  if (!user) throw new Error('Not authenticated')
  
  const token = await user.getIdToken()
  const res = await fetch(`${BASE}${path}`, {
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
      ...(opts.headers || {})
    },
    ...opts,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || `HTTP ${res.status}`)
  }
  return res.headers.get('content-type')?.includes('application/json')
    ? res.json()
    : res.text()
}

export const api = {
  consent: ({ user_id, consent, username }) =>
    http('/consent', { method: 'POST', body: JSON.stringify({ user_id, consent, username }) }),
  sendMessage: ({ user_id, session, message }) =>
    http('/dialogflow-webhook', {
      method: 'POST',
      body: JSON.stringify({
        session,
        messages: [{ text: { text: [message] } }],
        sessionInfo: { parameters: { user_id } },
      }),
    }),
  deleteMemories: ({ user_id }) =>
    http('/delete_memories', { method: 'POST', body: JSON.stringify({ user_id }) }),
}

