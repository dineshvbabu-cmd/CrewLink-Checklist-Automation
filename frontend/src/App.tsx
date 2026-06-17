import { BrowserRouter, Route, Routes, useLocation } from 'react-router-dom'
import Navbar from './components/Common/Navbar'
import CrewListPage from './pages/CrewListPage'
import SeafarerProfilePage from './pages/SeafarerProfilePage'
import SelfServiceApprovalPage from './pages/SelfServiceApprovalPage'

function AppShell() {
  const location = useLocation()
  const hideNavbar = location.pathname.startsWith('/approval/')

  return (
    <div className="min-h-screen flex flex-col bg-gray-100">
      {!hideNavbar && <Navbar />}
      <main className="flex-1">
        <Routes>
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
    <BrowserRouter>
      <AppShell />
    </BrowserRouter>
  )
}
