import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getUser, clearAuth } from '../api/client'

function Photo({ url }) {
  const [src, setSrc] = useState(null)
  useEffect(() => { api.photoBlob(url).then(setSrc).catch(() => {}) }, [url])
  return src ? <img src={src} alt="evidence" className="photo-preview" /> : <p style={{ fontSize: 12 }}>Loading photo…</p>
}

export default function Generator() {
  const user = getUser()
  const nav = useNavigate()
  const [data, setData] = useState(null)
  const [msg, setMsg] = useState(null)
  const [text, setText] = useState({})

  async function load() {
    try { setData(await api.generatorMe()) } catch (e) { setMsg({ type: 'err', text: e.message }) }
  }
  useEffect(() => { load() }, [])

  async function contest(id) {
    try {
      await api.contest(id, text[id] || '')
      setMsg({ type: 'ok', text: 'Contest submitted. The case officer will review it.' })
      load()
    } catch (e) { setMsg({ type: 'err', text: e.message }) }
  }

  return (
    <div className="app-shell">
      <div className="topbar">
        <div>
          <h1>PROOF-TO-VALUE</h1>
          <div className="role">{user?.name} · Generator</div>
        </div>
        <button onClick={() => { clearAuth(); nav('/login') }}>Logout</button>
      </div>
      <div className="content">
        {msg && <div className={`msg msg-${msg.type}`}>{msg.text}</div>}
        {data && (
          <>
            <div className="card">
              <h3>{data.generator.name}</h3>
              <div className="stat-grid">
                <div className="stat"><div className="num">{data.summary.sorted}</div><div className="lbl">Sorted</div></div>
                <div className="stat"><div className="num">{data.summary.mixed}</div><div className="lbl">Mixed</div></div>
                <div className="stat"><div className="num">{data.summary.unclear}</div><div className="lbl">Unclear</div></div>
              </div>
            </div>
            <h3 style={{ margin: '12px 0' }}>Notices and evidence</h3>
            {data.notices.length === 0 && <div className="empty">No notices issued.</div>}
            {data.notices.map((n) => (
              <div key={n.id} className="notice-item">
                <span className={`level level-${n.level}`}>{n.level.replace('_', ' ')}</span>
                <p style={{ fontSize: 13, margin: '4px 0' }}>{n.bin_label} · {new Date(n.server_time).toLocaleString()}</p>
                <Photo url={n.photo_url} />
                <p style={{ fontSize: 11, color: '#718096', wordBreak: 'break-all' }}>Evidence hash: {n.this_hash}</p>
                <p style={{ fontSize: 12, margin: '6px 0' }}>Status: <strong>{n.status}</strong>{n.officer_remark ? ` · Officer: ${n.officer_remark}` : ''}</p>
                {n.contest_text && <p style={{ fontSize: 12 }}>Your contest: {n.contest_text}</p>}
                {n.status === 'confirmed' && (
                  <>
                    <textarea rows={2} style={{ width: '100%', margin: '6px 0' }} placeholder="Why do you contest this notice?"
                      value={text[n.id] || ''} onChange={(e) => setText({ ...text, [n.id]: e.target.value })} />
                    <button className="btn btn-orange" onClick={() => contest(n.id)}>Contest this notice</button>
                  </>
                )}
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
