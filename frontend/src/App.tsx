import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './auth'
import Navbar from './components/Common/Navbar'
import CrewListPage from './pages/CrewListPage'
import LoginPage from './pages/LoginPage'
import SeafarerProfilePage from './pages/SeafarerProfilePage'
import SelfServiceApprovalPage from './pages/SelfServiceApprovalPage'

function AppShell() {
  const { user, loading } = useAuth()
  const location = useLocation()
  const hideNavbar = location.pathname.startsWith('/approval/')
  const isLoginPage = location.pathname === '/login'

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-100 text-slate-500">
        Loading Crewlink workspace...
      </div>
    )
  }

  if (!hideNavbar && !isLoginPage && !user) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-100">
      {!hideNavbar && <Navbar />}
      <main className="flex-1">
        <Routes>
          <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
          <Route path="/" element={<CrewListPage />} />
          <Route path="/seafarer/:id" element={<SeafarerProfilePage />} />
          <Route path="/approval/:token" element={<SelfServiceApprovalPage />} />
        </Routes>
      </main>
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppShell />
      </BrowserRouter>
    </AuthProvider>
  )
}
