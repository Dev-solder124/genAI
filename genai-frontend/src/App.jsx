import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext.jsx'
import ProtectedRoute from './components/ProtectedRoute.jsx'
import Onboarding from './pages/Onboarding.jsx'
import Chat from './pages/Chat.jsx'
import './index.css'

const LOGO_SVG = '/brand/empathicai-logo.svg' // put your SVG here (public/brand/...) or replace with a hosted SVG link

function Header() {
  const { pathname } = useLocation()
  return (
    <header className="header card">
      <div className="brand">
        <img src={LOGO_SVG} alt="EmpathicAI logo" />
        <span className="brand-name">EmpathicAI</span>
      </div>
      <div className="center">{pathname.startsWith('/chat') ? 'Chat' : 'Welcome'}</div>
      <nav className="right" style={{ display: 'flex', gap: 12 }}>
        <Link className="link" to="/chat">Chat</Link>
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






