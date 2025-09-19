const KEYS = {
  users: 'eb_users_data',
  history: 'eb_chat_history',
  current: 'eb_current_user_id',
}

export function sanitizeId(input) {
  const sanitized = (input || '').replace(/[^a-zA-Z0-9_-]/g, '_')
  if (!sanitized) return 'anonymous_user'
  return /^\d/.test(sanitized) ? `user_${sanitized}` : sanitized
}

export function loadUsers() {
  try { return JSON.parse(localStorage.getItem(KEYS.users) || '{}') } catch { return {} }
}
export function saveUsers(obj) {
  localStorage.setItem(KEYS.users, JSON.stringify(obj))
}

export function loadHistory() {
  try { return JSON.parse(localStorage.getItem(KEYS.history) || '[]') } catch { return [] }
}
export function saveHistory(arr) {
  const recent = arr.length > 1000 ? arr.slice(-1000) : arr
  localStorage.setItem(KEYS.history, JSON.stringify(recent))
}

export function getCurrentUserId() { return localStorage.getItem(KEYS.current) }
export function setCurrentUserId(id) { localStorage.setItem(KEYS.current, id) }
export function clearCurrentUser() { localStorage.removeItem(KEYS.current) }

export function addHistoryEntry({ user_id, session_id, user_message, bot_response }) {
  const all = loadHistory()
  all.push({ timestamp: new Date().toISOString(), user_id, session_id, user_message, bot_response })
  saveHistory(all)
}

export function userMessageCount(user_id) {
  return loadHistory().filter(h => h.user_id === user_id).length
}
export function userRecentHistory(user_id, limit = 10) {
  const list = loadHistory().filter(h => h.user_id === user_id)
  return list.slice(-limit)
}
export function userFullHistory(user_id) {
  return loadHistory().filter(h => h.user_id === user_id)
}

export function removeUser(user_id) {
  const users = loadUsers(); delete users[user_id]; saveUsers(users)
  const kept = loadHistory().filter(h => h.user_id !== user_id); saveHistory(kept)
  if (getCurrentUserId() === user_id) clearCurrentUser()
}
