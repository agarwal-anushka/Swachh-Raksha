import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, setAuth } from '../api/client'

const ROLE_ROUTES = {
  admin: '/admin',
  collector: '/collector',
  reviewer: '/reviewer',
  officer: '/officer',
}

export default function Login() {
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setErr('')
    setLoading(true)
    try {
      const data = await api.login(email, password)
      setAuth(data.access_token, { name: data.name, role: data.role, email })
      nav(ROLE_ROUTES[data.role] || '/login')
    } catch {
      setErr('Invalid email or password')
    } finally {
      setLoading(false)
    }
  }

  function quick(role) {
    const map = {
      collector: ['collector@ptv.local', 'collect123'],
      reviewer: ['reviewer1@ptv.local', 'review123'],
      officer: ['officer@ptv.local', 'officer123'],
      admin: ['admin@ptv.local', 'admin123'],
    }
    setEmail(map[role][0])
    setPassword(map[role][1])
  }

  return (
    <div className="login-wrap">
      <div className="login-box">
        <h1>Proof-to-Value</h1>
        <p className="sub">Evidence system for Gwalior BWGs</p>

        {err && <div className="msg msg-err">{err}</div>}

        <form onSubmit={handleSubmit}>
          <label>Email</label>
          <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@ptv.local" required />
          <label>Password</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button className="btn btn-primary" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div style={{ marginTop: 20, fontSize: 12, color: '#4A5568' }}>
          <p style={{ marginBottom: 8 }}>Quick login (pilot):</p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {['collector', 'reviewer', 'officer', 'admin'].map((r) => (
              <button key={r} type="button" onClick={() => quick(r)}
                style={{ fontSize: 11, padding: '4px 10px', borderRadius: 6, border: '1px solid #cbd5e0', background: '#edf2f7', cursor: 'pointer' }}>
                {r}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
