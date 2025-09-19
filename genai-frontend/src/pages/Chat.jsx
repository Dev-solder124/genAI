import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../lib/api.js'
import {
  getCurrentUserId, loadUsers, saveUsers, addHistoryEntry, userRecentHistory
} from '../lib/storage.js'
import styles from './Chat.module.css'

export default function Chat() {
  const user_id = getCurrentUserId()
  const [session, setSession] = useState(() => `session_${Date.now()}_${user_id || 'anon'}`)
  const [messages, setMessages] = useState(() => userRecentHistory(user_id || '', 30))
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const listRef = useRef(null)

  const username = useMemo(() => (loadUsers()[user_id]?.username || 'User'), [user_id])

  useEffect(() => { listRef.current?.scrollTo(0, listRef.current.scrollHeight) }, [messages])

  function newSession() { setSession(`session_${Date.now()}_${user_id || 'anon'}`) }

  async function send() {
    if (!input.trim() || !user_id) return
    const text = input.trim()
    setInput('')

    const userEntry = { timestamp: new Date().toISOString(), user_id, session_id: session, user_message: text, bot_response: '' }
    setMessages(m => [...m, userEntry])

    try {
      const data = await api.sendMessage({ user_id, session, message: text })
      const reply = data?.fulfillment_response?.messages?.[0]?.text?.text?.[0] ?? '…'
      const botEntry = { timestamp: new Date().toISOString(), user_id, session_id: session, user_message: '', bot_response: reply }
      addHistoryEntry(userEntry)
      addHistoryEntry(botEntry)
      setMessages(m => [...m.slice(0, -1), userEntry, botEntry])

      const users = loadUsers()
      if (users[user_id]) { users[user_id].last_chat_date = new Date().toISOString(); saveUsers(users) }
    } catch (e) {
      setError(e.message || 'Network error'); setTimeout(() => setError(''), 3000)
    }
  }

  if (!user_id) return <div className="card">No user selected. Please create a user on the Welcome screen.</div>

  return (
    <div className={`card ${styles.shell}`}>
      <div className={styles.topBar}>
        <div className="label">User: {username}</div>
        <button className="button" onClick={newSession}>New Session</button>
      </div>
      <div ref={listRef} className={styles.list}>
        {messages.map((m, i) => {
          const role = m.user_message ? 'user' : 'bot'
          const text = m.user_message || m.bot_response
          return (
            <div key={i} className={`${styles.row} ${role === 'user' ? styles.right : styles.left}`}>
              <div className={`${styles.bubble} ${role === 'user' ? styles.user : styles.bot}`}>{text}</div>
            </div>
          )
        })}
      </div>
      <div className={styles.inputRow}>
        <input
          className="input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Type a message"
        />
        <button className="button" onClick={send}>Send</button>
      </div>
      {error && <p style={{ color: '#ef4444', marginTop: 6 }}>{error}</p>}
    </div>
  )
}

