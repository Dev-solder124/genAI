import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../lib/api.js'
import { useAuth } from '../contexts/AuthContext.jsx'
import styles from './Chat.module.css'

function now() {
  const d = new Date()
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

export default function Chat() {
  const { user, userProfile } = useAuth()
  const [session, setSession] = useState(() =>
    `projects/${import.meta.env.VITE_FIREBASE_PROJECT_ID}/agent/sessions/session_${Date.now()}_${user?.uid || 'anon'}`
  )
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [error, setError] = useState('')
  const listRef = useRef(null)

  const username = useMemo(
    () => userProfile?.profile?.username || (user?.isAnonymous ? 'Guest' : 'User'),
    [user, userProfile]
  )

  useEffect(() => {
    listRef.current?.scrollTo(0, listRef.current.scrollHeight)
  }, [messages])

  function newSession() {
    setSession(`projects/${import.meta.env.VITE_FIREBASE_PROJECT_ID}/agent/sessions/session_${Date.now()}_${user?.uid || 'anon'}`)
    setMessages([])
  }

  async function send() {
    if (!input.trim()) return
    const text = input.trim()
    setInput('')
    setMessages(m => [...m, { role: 'user', text, t: now() }])
    try {
      const data = await api.sendMessage({ session, message: text })
      const reply =
        data?.fulfillment_response?.messages?.[0]?.text?.text?.[0] ||
        data?.fulfillmentResponse?.messages?.[0]?.text?.text?.[0] ||
        data?.reply || '…'
      setMessages(m => [...m, { role: 'bot', text: reply, t: now() }])
    } catch (e) {
      setError(e.message || 'Network error')
      setTimeout(() => setError(''), 3000)
      setMessages(m => [...m, { role: 'bot', text: 'Request failed', t: now() }])
    }
  }

  return (
    <div className="card chat-shell">
      <div className="chat-top">
        <div className="label">User: {username}</div>
        <button className="button" onClick={newSession}>New Session</button>
      </div>
      <div ref={listRef} className="chat-list">
        {messages.map((m, i) => (
          <div key={i} className={`row ${m.role === 'user' ? 'right' : 'left'}`}>
            <div className={`bubble ${m.role === 'user' ? 'user' : 'bot'}`}>
              {m.text}
              <span className="timestamp">{m.t}</span>
            </div>
          </div>
        ))}
      </div>
      <div className="chat-input-row">
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



