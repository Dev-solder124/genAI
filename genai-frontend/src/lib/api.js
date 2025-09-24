// Updated api.js - Better handling for anonymous users
import { auth, ensureTokenReady } from './auth'

// Remove the /api prefix since your backend doesn't use it
const BASE = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')

class ApiError extends Error {
  constructor(message, status, code) {
    super(message)
    this.status = status
    this.code = code
  }
}

const MAX_RETRIES = 3
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
    // For anonymous users, ensure token is ready before making requests
    let token
    if (user.isAnonymous) {
      console.log('Anonymous user detected, ensuring token is ready...')
      token = await ensureTokenReady()
    } else {
      token = await user.getIdToken(retryCount > 0) // Force refresh on retry
    }
    
    console.log(`API Call: ${opts.method || 'GET'} ${BASE}${path}`)
    console.log(`User type: ${user.isAnonymous ? 'Anonymous' : 'Authenticated'}`)
    
    const res = await fetch(`${BASE}${path}`, {
      headers: { 
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...(opts.headers || {})
      },
      ...opts,
    })

    console.log(`API Response: ${res.status} ${res.statusText}`)

    if (!res.ok) {
      let errorData
      const contentType = res.headers.get('content-type')
      
      if (contentType?.includes('application/json')) {
        try {
          errorData = await res.json()
        } catch (e) {
          errorData = { error: `HTTP ${res.status}` }
        }
      } else {
        const text = await res.text().catch(() => '')
        errorData = { error: text || `HTTP ${res.status}` }
      }

      console.log('API Error Data:', errorData)

      // Handle specific error codes for anonymous users
      if (res.status === 401) {
        if (errorData.code === 'anonymous_auth_failed' || errorData.code === 'token_expired') {
          console.log('Anonymous authentication issue, retrying with fresh token...')
          if (retryCount < MAX_RETRIES) {
            await sleep(RETRY_DELAY * (retryCount + 1))
            return http(path, opts, retryCount + 1)
          }
        } else if (retryCount < MAX_RETRIES) {
          console.log('Token expired, retrying with fresh token...')
          await sleep(RETRY_DELAY)
          return http(path, opts, retryCount + 1)
        }
      }

      // Handle specific error messages for anonymous users
      let errorMessage = errorData.error || errorData.message || `HTTP ${res.status}`
      if (errorData.code === 'anonymous_auth_failed') {
        errorMessage = 'Guest authentication failed. Please try signing in again.'
      }

      throw new ApiError(
        errorMessage,
        res.status,
        errorData.code || (
          res.status === 401 ? 'unauthorized' :
          res.status === 403 ? 'forbidden' :
          res.status === 404 ? 'not_found' :
          res.status === 429 ? 'rate_limited' :
          'server_error'
        )
      )
    }

    const responseData = res.headers.get('content-type')?.includes('application/json')
      ? await res.json()
      : await res.text()
    
    console.log('API Success Data:', responseData)
    return responseData
  } catch (error) {
    console.error('API Error:', error)
    if (error instanceof ApiError) throw error
    
    // Network or other errors
    throw new ApiError(
      error.message || 'Network error', 
      0, 
      'network_error'
    )
  }
}

export const api = {
  // Login endpoint - matches your backend
  login: async () => {
    // Add extra delay for anonymous users to ensure token is fully ready
    const user = auth.currentUser
    if (user && user.isAnonymous) {
      console.log('Anonymous user login, waiting for token readiness...')
      await sleep(1000)
    }
    return http('/login', { method: 'POST' })
  },
  
  // Consent endpoint - fixed to not pass user_id (backend gets it from token)
  consent: ({ consent, username }) =>
    http('/consent', { 
      method: 'POST', 
      body: JSON.stringify({ consent, username }) 
    }),
    
  // Send message endpoint - fixed to match your backend's expected format
  sendMessage: ({ session, message }) =>
    http('/dialogflow-webhook', {
      method: 'POST',
      body: JSON.stringify({
        session: session || `session_${Date.now()}`,
        messages: [{ 
          text: { 
            text: [message] 
          } 
        }],
        sessionInfo: { 
          parameters: {} 
        },
        // Add the text field that your backend also checks for
        text: message
      }),
    }),
  
  // Delete memories endpoint - fixed to pass user_id
  deleteMemories: ({ user_id }) =>
    http('/delete_memories', { 
      method: 'POST', 
      body: JSON.stringify({ user_id }) 
    }),

  // Add a health check endpoint for debugging
  healthCheck: () => http('/health', { method: 'GET' }),

  // Add debug endpoints for troubleshooting
  debugToken: () => http('/debug/token', { method: 'POST' }),
}