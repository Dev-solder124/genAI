const BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/$/, '')

async function http(path, opts = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) },
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

