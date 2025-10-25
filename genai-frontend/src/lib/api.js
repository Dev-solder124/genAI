import { auth } from './auth'

const BASE = (import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '')

class ApiError extends Error {
  constructor(message, status, code) {
    super(message)
    this.status = status
    this.code = code
  }
}

const MAX_RETRIES = 2
const RETRY_DELAY = 1000 // 1 second

async function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

async function http(path, opts = {}, retryCount = 0) {
  const user = auth.currentUser
  if (!user) {
    throw new ApiError('Not authenticated', 401, 'unauthenticated')
  }
  
  try {
    const token = await user.getIdToken(retryCount > 0) // Force refresh on retry
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
      const status = res.status

      // Token expired, retry with fresh token
      if (status === 401 && retryCount < MAX_RETRIES) {
        await sleep(RETRY_DELAY)
        return http(path, opts, retryCount + 1)
      }

      throw new ApiError(
        text || `HTTP ${status}`,
        status,
        status === 401 ? 'unauthorized' :
        status === 403 ? 'forbidden' :
        status === 404 ? 'not_found' :
        'unknown'
      )
    }

    return res.headers.get('content-type')?.includes('application/json')
      ? res.json()
      : res.text()
  } catch (error) {
    if (error instanceof ApiError) throw error
    throw new ApiError(error.message, 500, 'network_error')
  }
}

export const api = {
  login: () => http('/login', { method: 'POST' }),
  
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
  
  // FIX: Add the user_id to the request body
  deleteMemories: ({ user_id }) =>
    http('/delete_memories', { 
      method: 'POST', 
      body: JSON.stringify({ user_id }) 
    }),
  
  resetInstructions: () =>
    http('/reset_instructions', { method: 'POST' }),
}