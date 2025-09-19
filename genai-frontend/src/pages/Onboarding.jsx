import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api.js'
import { sanitizeId, loadUsers, saveUsers, setCurrentUserId } from '../lib/storage.js'
import styles from './Onboarding.module.css'

export default function Onboarding() {
  const [username, setUsername] = useState('')
  const [customId, setCustomId] = useState('')
  const [consent, setConsent] = useState(true)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const nav = useNavigate()

  async function onSubmit(e) {
    e.preventDefault()
    setError('')
    if (!username.trim()) return setError('Enter a username')
    if (!consent) return setError('Please accept consent to continue')

    let id = sanitizeId(customId || username)
    const users = loadUsers()
    if (users[id]) return setError('User ID already exists, try another')

    const now = new Date().toISOString()
    const user_data = { user_id: id, username, consent: null, created_date: now, last_chat_date: now }
    users[id] = user_data
    saveUsers(users)

    setLoading(true)
    try {
      await api.consent({ user_id: id, consent: true, username })
      users[id].consent = true
      saveUsers(users)
      setCurrentUserId(id)
      nav('/chat')
    } catch (err) {
      setError(err.message || 'Failed to sync consent')
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={onSubmit} className={`card ${styles.wrap}`}>
      <h2 className={styles.title}>Create your profile</h2>
      <div className={styles.row}>
        <label className="label">Username</label>
        <input className="input" value={username} onChange={e => setUsername(e.target.value)} placeholder="Your name" />
      </div>
      <div className={styles.row}>
        <label className="label">User ID (optional)</label>
        <input className="input" value={customId} onChange={e => setCustomId(e.target.value)} placeholder="letters, digits, _ or -" />
        <div className="label">Will be sanitized: {sanitizeId(customId || username || 'anonymous_user')}</div>
      </div>
      <label className={styles.consentLine}>
        <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />
        <span>I agree the assistant may remember helpful things between sessions.</span>
      </label>
      <button className="button" type="submit" disabled={loading || !username.trim()}>{loading ? 'Creating…' : 'Enter Chat'}</button>
      {error && <p className={styles.error}>{error}</p>}
    </form>
  )
}
