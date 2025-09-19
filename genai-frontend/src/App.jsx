import { BrowserRouter, Routes, Route, useLocation, Link, useNavigate } from 'react-router-dom'
import Onboarding from './pages/Onboarding.jsx'
import Chat from './pages/Chat.jsx'
import Users from './pages/Users.jsx'
import Settings from './pages/Settings.jsx'

function Header() {
  const { pathname } = useLocation()
  const center = pathname.startsWith('/chat') ? 'Chat'
    : pathname.startsWith('/users') ? 'Users'
    : pathname.startsWith('/settings') ? 'Settings'
    : 'Welcome'
  const nav = useNavigate()
  return (
    <header className="header card">
      <div className="brand" onClick={() => nav('/')} style={{ cursor: 'pointer' }}>EmpathicAI</div>
      <div className="header-center">{center}</div>
      <nav className="header-right" style={{ display: 'flex', gap: 12 }}>
        <Link className="link" to="/chat">Chat</Link>
        <Link className="link" to="/users">Users</Link>
        <Link className="link" to="/settings">Settings</Link>
      </nav>
    </header>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="container">
        <Header />
        <Routes>
          <Route path="/" element={<Onboarding />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/users" element={<Users />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}



