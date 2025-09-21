import { BrowserRouter, Routes, Route, Link, useLocation, useNavigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext.jsx'
import { logout } from './lib/firebase.js'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Onboarding from './pages/Onboarding.jsx'
import Chat from './pages/Chat.jsx'
import './index.css'

const LOGO_SVG = '/brand/empathicai-logo.svg'

function Header() {
  const { pathname } = useLocation()
  const navigate = useNavigate()
  const { user } = useAuth()

  async function handleLogout() {
    try {
      await logout()                   // end Firebase session [web:881]
      navigate('/', { replace: true }) // leave protected route [web:726]
    } catch (e) {
      // optional: toast/log error
      console.error('Logout failed', e)
    }
  }

  return (
    <header className="header card">
      <div className="brand">
        <img src={LOGO_SVG} alt="EmpathicAI logo" />
        <span className="brand-name">EmpathicAI</span>
      </div>
      <div className="center">{pathname.startsWith('/chat') ? 'Chat' : 'Welcome'}</div>
      <nav className="right" style={{ display: 'flex', gap: 12 }}>
        <Link className="link" to="/chat"> </Link>
        {user ? (
          <button
            className="button secondary"
            onClick={handleLogout}
            aria-label="Log out"
          >
            Logout
          </button>
        ) : null}
      </nav>
    </header>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div className="container">
          <Header />
          <Routes>
            <Route path="/" element={<Onboarding />} />
            <Route path="/chat" element={<ProtectedRoute><Chat /></ProtectedRoute>} />
            <Route path="*" element={<Onboarding />} />
          </Routes>
        </div>
      </AuthProvider>
    </BrowserRouter>
  )
}





