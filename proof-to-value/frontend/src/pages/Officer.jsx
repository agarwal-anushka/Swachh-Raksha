import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getUser, clearAuth } from '../api/client'

export default function Officer() {
  const user = getUser()
  const nav = useNavigate()
  const [stats, setStats] = useState(null)
  const [notices, setNotices] = useState([])
  const [filter, setFilter] = useState('proposed')
  const [msg, setMsg] = useState(null)

  async function load() {
    try {
      const [s, n] = await Promise.all([
        api.dashboard(),
        api.listNotices(filter || undefined),
      ])
      setStats(s)
      setNotices(n)
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    }
  }

  useEffect(() => { load() }, [filter])

  async function act(id, action) {
    try {
      await api.noticeAction(id, action)
      setMsg({ type: 'ok', text: `Notice ${action}ed` })
      load()
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    }
  }

  function logout() {
    clearAuth()
    nav('/login')
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <div>
          <h1>PROOF-TO-VALUE</h1>
          <div className="role">{user?.name} · Case Officer</div>
        </div>
        <button onClick={logout}>Logout</button>
      </div>

      <div className="content">
        {msg && <div className={`msg msg-${msg.type}`}>{msg.text}</div>}

        {stats && (
          <div className="stat-grid">
            <div className="stat">
              <div className="num">{stats.total_evidence}</div>
              <div className="lbl">Photos</div>
            </div>
            <div className="stat">
              <div className="num">{stats.locked_verdicts}</div>
              <div className="lbl">Locked Verdicts</div>
            </div>
            <div className="stat">
              <div className="num">{stats.proposed_notices}</div>
              <div className="lbl">Proposed Notices</div>
            </div>
            <div className="stat">
              <div className="num">{stats.verdict_breakdown?.mixed || 0}</div>
              <div className="lbl">Mixed</div>
            </div>
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          {['proposed', 'confirmed', 'dismissed', ''].map((f) => (
            <button
              key={f || 'all'}
              onClick={() => setFilter(f)}
              style={{
                fontSize: 12, padding: '6px 12px', borderRadius: 20, cursor: 'pointer',
                border: filter === f ? 'none' : '1px solid #cbd5e0',
                background: filter === f ? '#1A3C34' : '#fff',
                color: filter === f ? '#fff' : '#4A5568',
              }}
            >
              {f || 'all'}
            </button>
          ))}
        </div>

        {notices.length === 0 ? (
          <div className="empty">No notices in this filter</div>
        ) : (
          notices.map((n) => (
            <div key={n.id} className="notice-item">
              <span className={`level level-${n.level}`}>{n.level.replace('_', ' ')}</span>
              <p style={{ fontSize: 13, margin: '4px 0' }}>
                Generator #{n.generator_id} · Evidence #{n.evidence_id}
              </p>
              <p style={{ fontSize: 11, color: '#718096' }}>
                {new Date(n.created_at).toLocaleString()} · {n.status}
              </p>
              {n.status === 'proposed' && (
                <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                  <button className="btn btn-ok" style={{ padding: '8px' }} onClick={() => act(n.id, 'confirm')}>
                    Confirm
                  </button>
                  <button className="btn btn-outline" style={{ padding: '8px' }} onClick={() => act(n.id, 'dismiss')}>
                    Dismiss
                  </button>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  )
}
