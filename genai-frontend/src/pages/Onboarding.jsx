import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { signInWithGoogle, signInAsGuest } from '../lib/firebase.js'
import { useAuth } from '../contexts/AuthContext.jsx'
import { api } from '../lib/api.js'
import styles from './Onboarding.module.css'

export default function Onboarding() {
  const { user, userProfile, setUserProfile } = useAuth()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [consent, setConsent] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    if (user && userProfile && userProfile.profile?.consent !== null && userProfile.profile?.consent !== undefined) {
      navigate('/chat', { replace: true })
    }
  }, [user, userProfile, navigate])

  async function handleGoogle() {
    setError(''); setLoading(true)
    try { await signInWithGoogle() } catch (e) { setError(e.message || 'Sign in failed') }
    finally { setLoading(false) }
  }
  async function handleGuest() {
    setError(''); setLoading(true)
    try { await signInAsGuest() } catch (e) { setError(e.message || 'Guest sign in failed') }
    finally { setLoading(false) }
  }
  async function saveConsent() {
    setError(''); setLoading(true)
    try {
      const res = await api.consent({ consent })
      const updated = { ...(userProfile || {}), profile: { ...(userProfile?.profile || {}), consent: res?.profile?.consent ?? consent } }
      setUserProfile(updated)
      navigate('/chat', { replace: true })
    } catch (e) {
      setError(e.message || 'Failed to save consent')
    } finally { setLoading(false) }
  }

  if (user && userProfile && (userProfile.profile?.consent === null || userProfile.profile?.consent === undefined)) {
    return (
      <div className="card" style={{ maxWidth: 560, margin: '0 auto' }}>
        <h2 className={styles.title}>Privacy & Memory Settings</h2>
        <p className="label">Allow remembering helpful things between sessions.</p>
        <label className={styles.line}>
          <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />
          <span>Enable long‑term memory</span>
        </label>
        <div style={{ display:'flex', gap:10 }}>
          <button className="button" onClick={saveConsent} disabled={loading}>{loading ? 'Saving…' : 'Continue'}</button>
          <button className="button secondary" onClick={() => { setConsent(false); saveConsent(); }} disabled={loading}>Skip</button>
        </div>
        {error && <p className={styles.error}>{error}</p>}
      </div>
    )
  }

  return (
    <div className="card" style={{ maxWidth: 560, margin: '0 auto' }}>
      <h2 className={styles.title}>Welcome to EmpathicAI</h2>
      <p className="label">Sign in to start chatting.</p>
      <div style={{ display:'flex', gap:10 }}>
        <button className="button" onClick={handleGoogle} disabled={loading}>
          {loading ? 'Signing in…' : '🔑 Sign in with Google'}
        </button>
        <button className="button secondary" onClick={handleGuest} disabled={loading}>
          {loading ? 'Signing in…' : '👤 Continue as Guest'}
        </button>
      </div>
      {error && <p className={styles.error}>{error}</p>}
    </div>
  )
}




