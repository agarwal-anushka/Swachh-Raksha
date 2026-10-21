import { Routes, Route, Navigate } from 'react-router-dom'
import { getUser } from './api/client'
import Login from './pages/Login'
import Collector from './pages/Collector'
import Reviewer from './pages/Reviewer'
import Officer from './pages/Officer'
import Admin from './pages/Admin'
import Generator from './pages/Generator'
import QrSheet from './pages/QrSheet'

function Private({ role, children }) {
  const user = getUser()
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role && user.role !== 'admin') {
    // allow admin everywhere
    if (user.role !== 'admin') return <Navigate to="/login" replace />
  }
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/collector" element={<Private role="collector"><Collector /></Private>} />
      <Route path="/reviewer" element={<Private role="reviewer"><Reviewer /></Private>} />
      <Route path="/officer" element={<Private role="officer"><Officer /></Private>} />
      <Route path="/generator" element={<Private role="generator"><Generator /></Private>} />
      <Route path="/qr-sheet" element={<Private role="admin"><QrSheet /></Private>} />
      <Route path="/admin" element={<Private role="admin"><Admin /></Private>} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
