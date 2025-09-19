import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../lib/api.js'
import {
  loadUsers, saveUsers, getCurrentUserId, setCurrentUserId,
  userMessageCount, removeUser
} from '../lib/storage.js'

export default function Users() {
  const [usersList, setUsersList] = useState([])
  const [busy, setBusy] = useState(false)
  const nav = useNavigate()
  const current = getCurrentUserId()

  function refresh() {
    const users = loadUsers()
    const rows = Object.entries(users).map(([id, u]) => ({
      user_id: id,
      username: u.username || 'Unknown',
      consent: u.consent,
      created_date: u.created_date || '',
      last_chat_date: u.last_chat_date || '',
      message_count: userMessageCount(id),
    }))
    rows.sort((a, b) => (b.last_chat_date || '').localeCompare(a.last_chat_date || ''))
    setUsersList(rows)
  }

  useEffect(() => { refresh() }, [])

  function selectUser(id) {
    setCurrentUserId(id)
    const users = loadUsers()
    if (users[id]) {
      users[id].last_chat_date = new Date().toISOString()
      saveUsers(users)
    }
    nav('/chat')
  }

  async function deleteUser(id) {
    if (!confirm('Delete server memories and local history for this user?')) return
    setBusy(true)
    try { await api.deleteMemories({ user_id: id }) } catch {}
    removeUser(id)
    refresh()
    setBusy(false)
  }

  return (
    <div className="card">
      <h3>Users</h3>
      {usersList.length === 0 && <p className="label">No users found.</p>}
      {usersList.map((u) => (
        <div key={u.user_id} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '8px 0', borderTop: '1px solid var(--border)' }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 600 }}>
              {u.username} {current === u.user_id ? '🟢' : '⚪'}
            </div>
            <div className="label">
              ID: {u.user_id} • Messages: {u.message_count || 0} • Last: {(u.last_chat_date || 'Never').slice(0,16)}
            </div>
          </div>
          <button className="button" onClick={() => selectUser(u.user_id)}>Use</button>
          <button className="button" disabled={busy} onClick={() => deleteUser(u.user_id)}>Delete</button>
        </div>
      ))}
    </div>
  )
}
