import { useMemo, useState } from 'react'
import {
  loadUsers, saveUsers, getCurrentUserId, userFullHistory
} from '../lib/storage.js'

export default function Settings() {
  const id = getCurrentUserId()
  const users = loadUsers()
  const me = users[id] || {}
  const [username, setUsername] = useState(me.username || '')

  const sessions = useMemo(() => {
    const list = userFullHistory(id)
    const set = new Set(list.map(h => h.session_id).filter(Boolean))
    return set.size
  }, [id])

  function changeUsername() {
    if (!username.trim()) return
    users[id].username = username.trim()
    saveUsers(users)
    alert('Username updated')
  }

  function resetConsent() {
    if (!confirm('Reset consent? The app will ask again during chat.')) return
    users[id].consent = null
    saveUsers(users)
    alert('Consent reset; next chat will ask again.')
  }

  if (!id) return <div className="card">No user selected.</div>

  return (
    <div className="card" style={{ display: 'grid', gap: 12 }}>
      <div><strong>User ID:</strong> {id}</div>
      <div style={{ display: 'grid', gap: 6 }}>
        <label className="label">Username</label>
        <input className="input" value={username} onChange={e => setUsername(e.target.value)} />
        <button className="button" onClick={changeUsername}>Save</button>
      </div>
      <div className="label">Created: {(me.created_date || '—').slice(0,10)} • Sessions: {sessions}</div>
      <button className="button" onClick={resetConsent}>Reset Consent</button>
    </div>
  )
}
