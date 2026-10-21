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
  const [chain, setChain] = useState(null)
  const [missed, setMissed] = useState([])
  const [revs, setRevs] = useState([])
  const [cols, setCols] = useState([])

  async function load() {
    try {
      const [s, n, m] = await Promise.all([
        api.dashboard(),
        api.listNotices(filter || undefined),
        api.missed(),
      ])
      setStats(s)
      setNotices(n)
      setMissed(m)
      setRevs(await api.reviewers())
      setCols(await api.collectors())
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    }
  }

  useEffect(() => { load() }, [filter])

  async function report() {
    try {
      const url = await api.downloadReport()
      const a = document.createElement('a'); a.href = url; a.download = 'compliance_report.csv'; a.click()
    } catch (e) { setMsg({ type: 'err', text: e.message }) }
  }

  async function verify() {
    try { setChain(await api.verifyChain()) } catch (e) { setMsg({ type: 'err', text: e.message }) }
  }

  async function tamper(id) {
    await api.demoTamper(id); setChain(null); setMsg({ type: 'ok', text: `Demo: evidence #${id} edited directly in the database` })
  }

  async function restore() {
    await api.demoRestore(); setChain(null); setMsg({ type: 'ok', text: 'Demo: record restored' })
  }

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

        <div className="card">
          <h3>Evidence chain integrity</h3>
          <button className="btn btn-primary" onClick={verify}>Verify chain</button>
          {chain && (
            <div className={`msg ${chain.ok ? 'msg-ok' : 'msg-err'}`} style={{ marginTop: 10 }}>
              {chain.ok
                ? `Chain intact: ${chain.total} records verified. Head ${chain.head?.slice(0, 16)}…`
                : `TAMPERING DETECTED at evidence #${chain.broken_evidence_id}: ${chain.reason}`}
            </div>
          )}
          {stats?.demo && (
            <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <button className="btn btn-outline" style={{ padding: 8 }} onClick={() => tamper(1)}>Demo: edit record #1</button>
              <button className="btn btn-outline" style={{ padding: 8 }} onClick={restore}>Demo: restore</button>
            </div>
          )}
        </div>

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
          {['proposed', 'confirmed', 'contested', 'dismissed', ''].map((f) => (
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
          notices.map((n) => <Case key={n.id} n={n} act={act} />)
        )}

        <div className="card" style={{ marginTop: 16 }}>
          <h3>Reviewer quality (hidden test photos)</h3>
          {revs.map((r) => (
            <p key={r.name} style={{ fontSize: 12, margin: '4px 0' }}>
              {r.name} ({r.zone}) · test accuracy {r.test_accuracy == null ? 'n/a' : `${r.test_accuracy}% (${r.tests_correct}/${r.tests_answered})`} · agreed with final verdict {r.agree_with_majority}/{r.graded}
            </p>
          ))}
        </div>

        <div className="card">
          <h3>Collectors and bonus</h3>
          {cols.map((c) => (
            <p key={c.name} style={{ fontSize: 12, margin: '4px 0' }}>
              {c.name} · done {c.done} · missed {c.missed} · verified clean {c.verified_clean} · bonus ₹{c.bonus_rupees}
            </p>
          ))}
        </div>

        <div className="card">
          <h3>Monthly compliance pack</h3>
          <button className="btn btn-primary" onClick={report}>Download this month (CSV)</button>
        </div>

        {missed.length > 0 && (
          <div className="card" style={{ marginTop: 16 }}>
            <h3>Missed city pickups ({stats?.missed_pickups})</h3>
            {missed.map((m) => (
              <p key={m.id} style={{ fontSize: 12, margin: '4px 0' }}>
                {new Date(m.at).toLocaleDateString()} · {m.bin_label} · {m.reason || 'no reason given'}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function Case({ n, act }) {
  const [src, setSrc] = useState(null)
  useEffect(() => { if (n.photo_url) api.photoBlob(n.photo_url).then(setSrc).catch(() => {}) }, [n.photo_url])
  return (
    <div className="notice-item">
      <span className={`level level-${n.level}`}>{n.level.replace('_', ' ')}</span>
      <p style={{ fontSize: 14, margin: '6px 0 2px' }}><strong>{n.generator_name}</strong> · {n.bin_label}</p>
      <p style={{ fontSize: 12, color: '#4A5568' }}>
        Reviewer votes: {n.votes ? `${n.votes.mixed} mixed / ${n.votes.sorted} sorted / ${n.votes.unclear} unclear` : '-'}
        {' '}· Mixed in last 30 days: {n.mixed_last_30_days} · all time: {n.mixed_all_time}
      </p>
      {src && <img src={src} alt="evidence" className="photo-preview" />}
      <p style={{ fontSize: 11, color: '#718096', wordBreak: 'break-all' }}>
        Captured {new Date(n.server_time).toLocaleString()}
        {n.latitude != null && ` · ${n.latitude.toFixed(5)}, ${n.longitude.toFixed(5)}`}<br />
        Hash {n.this_hash}
      </p>
      {n.contest_text && <p style={{ fontSize: 12, margin: '6px 0' }}>Generator contest: {n.contest_text}</p>}
      <p style={{ fontSize: 11, color: '#718096' }}>{n.status}</p>
      {n.status === 'proposed' && (
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <button className="btn btn-ok" style={{ padding: 8 }} onClick={() => act(n.id, 'confirm')}>Confirm</button>
          <button className="btn btn-outline" style={{ padding: 8 }} onClick={() => act(n.id, 'dismiss')}>Dismiss</button>
        </div>
      )}
      {n.status === 'contested' && (
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <button className="btn btn-ok" style={{ padding: 8 }} onClick={() => act(n.id, 'uphold')}>Uphold</button>
          <button className="btn btn-outline" style={{ padding: 8 }} onClick={() => act(n.id, 'withdraw')}>Withdraw</button>
        </div>
      )}
    </div>
  )
}
