import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getUser, clearAuth } from '../api/client'

export default function Reviewer() {
  const user = getUser()
  const nav = useNavigate()
  const [queue, setQueue] = useState([])
  const [current, setCurrent] = useState(null)
  const [photo, setPhoto] = useState(null)
  const [msg, setMsg] = useState(null)
  const [loading, setLoading] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api.reviewQueue()
      setQueue(data)
      setCurrent(data[0] || null)
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    let alive = true
    setPhoto(null)
    if (current) api.photoBlob(current.photo_url).then((u) => alive && setPhoto(u)).catch(() => {})
    return () => { alive = false }
  }, [current])

  async function grade(verdict) {
    if (!current) return
    setLoading(true)
    setMsg(null)
    try {
      await api.submitReview(current.ref, verdict)
      setMsg({ type: 'ok', text: `Marked as ${verdict.toUpperCase()}` })
      // Remove from local queue and show next
      const next = queue.filter((q) => q.ref !== current.ref)
      setQueue(next)
      setCurrent(next[0] || null)
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    } finally {
      setLoading(false)
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
          <div className="role">{user?.name} · Reviewer</div>
        </div>
        <button onClick={logout}>Logout</button>
      </div>

      <div className="content">
        {msg && <div className={`msg msg-${msg.type}`}>{msg.text}</div>}

        {!current ? (
          <div className="empty">
            <p style={{ fontSize: 18, marginBottom: 8 }}>All clear</p>
            <p>No photos waiting for review.</p>
            <button className="btn btn-outline" style={{ marginTop: 16, maxWidth: 200 }} onClick={load}>
              Refresh
            </button>
          </div>
        ) : (
          <>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                <h3>Photo to grade</h3>
              </div>
              <p style={{ fontSize: 12, color: '#4A5568', marginBottom: 10 }}>
                Blind review: no location, owner or bin shown · {queue.length} in queue
              </p>
              {photo ? <img src={photo} alt="evidence" className="photo-preview" /> : <p>Loading photo…</p>}
            </div>

            <div className="btn-row">
              <button className="btn btn-ok" disabled={loading} onClick={() => grade('sorted')}>
                Sorted
              </button>
              <button className="btn btn-orange" disabled={loading} onClick={() => grade('mixed')}>
                Mixed
              </button>
              <button className="btn btn-outline" disabled={loading} onClick={() => grade('unclear')}>
                Unclear
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
