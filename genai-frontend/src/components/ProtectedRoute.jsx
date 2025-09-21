import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext.jsx'

export default function ProtectedRoute({ children }) {
  const { user, userProfile, loading } = useAuth()
  if (loading) return <div className="card">Loading…</div>
  if (!user || !userProfile) return <Navigate to="/" replace />
  return children
}

