import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getUser, clearAuth } from '../api/client'

export default function Collector() {
  const user = getUser()
  const nav = useNavigate()
  const [qr, setQr] = useState('')
  const [bin, setBin] = useState(null)
  const [photo, setPhoto] = useState(null)
  const [preview, setPreview] = useState(null)
  const [msg, setMsg] = useState(null)
  const [loading, setLoading] = useState(false)

  async function lookupBin() {
    setMsg(null)
    setBin(null)
    try {
      const data = await api.getBin(qr.trim())
      setBin(data)
    } catch (e) {
      setMsg({ type: 'err', text: e.message || 'Bin not found' })
    }
  }

  function onPhoto(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setPhoto(f)
    setPreview(URL.createObjectURL(f))
  }

  async function submit(status) {
    if (!bin) return
    if (status === 'done' && !photo) {
      setMsg({ type: 'err', text: 'Photo required for completed pickup' })
      return
    }
    setLoading(true)
    setMsg(null)
    try {
      const fd = new FormData()
      fd.append('bin_qr', bin.qr_code)
      fd.append('status', status)
      fd.append('device_time', new Date().toISOString())
      if (photo) fd.append('photo', photo)
      await api.submitPickup(fd)
      setMsg({ type: 'ok', text: status === 'done' ? 'Pickup + photo submitted!' : 'Marked as missed' })
      setBin(null)
      setQr('')
      setPhoto(null)
      setPreview(null)
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
          <div className="role">{user?.name} · Collector</div>
        </div>
        <button onClick={logout}>Logout</button>
      </div>

      <div className="content">
        {msg && <div className={`msg msg-${msg.type}`}>{msg.text}</div>}

        <div className="card">
          <h3>Scan / Enter QR Code</h3>
          <input
            value={qr}
            onChange={(e) => setQr(e.target.value)}
            placeholder="PTV-2026-00001"
          />
          <button className="btn btn-primary" onClick={lookupBin} disabled={!qr.trim()}>
            Lookup Bin
          </button>
        </div>

        {bin && (
          <div className="card">
            <h3>Bin Found</h3>
            <div className="qr-display">{bin.qr_code}</div>
            <p style={{ fontSize: 14, marginBottom: 4 }}>
              <strong>{bin.generator_name}</strong>
            </p>
            <p style={{ fontSize: 13, color: '#4A5568', marginBottom: 12 }}>
              Stream: <span className="badge">{bin.stream}</span>
              {bin.label && <> · {bin.label}</>}
            </p>

            <label>Photo of open bin</label>
            <input type="file" accept="image/*" capture="environment" onChange={onPhoto} />
            {preview && <img src={preview} alt="preview" className="photo-preview" />}

            <button
              className="btn btn-ok"
              onClick={() => submit('done')}
              disabled={loading || !photo}
            >
              {loading ? 'Submitting…' : 'Submit Clean Pickup'}
            </button>
            <button
              className="btn btn-outline"
              onClick={() => submit('missed')}
              disabled={loading}
            >
              Mark Missed
            </button>
          </div>
        )}

        <div className="card" style={{ fontSize: 12, color: '#4A5568' }}>
          <strong>Pilot QR codes:</strong>
          <div style={{ marginTop: 6, lineHeight: 1.7 }}>
            PTV-2026-00001 (Hostel A – Wet)<br />
            PTV-2026-00002 (Hostel A – Dry)<br />
            PTV-2026-00003 (Mess – Wet)<br />
            PTV-2026-00004 (Mess – Dry)<br />
            PTV-2026-00005 (Academic C – Wet)
          </div>
        </div>
      </div>
    </div>
  )
}
