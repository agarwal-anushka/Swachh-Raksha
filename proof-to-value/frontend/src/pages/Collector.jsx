import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getUser, clearAuth } from '../api/client'
import { compress, enqueue, listQueue, removeFromQueue } from '../api/offline'

export default function Collector() {
  const user = getUser()
  const nav = useNavigate()
  const [qr, setQr] = useState('')
  const [bin, setBin] = useState(null)
  const [photo, setPhoto] = useState(null)
  const [preview, setPreview] = useState(null)
  const [msg, setMsg] = useState(null)
  const [loading, setLoading] = useState(false)
  const [scanning, setScanning] = useState(false)
  const [gps, setGps] = useState(null)
  const [stats, setStats] = useState(null)
  const [pending, setPending] = useState(0)
  const videoRef = useRef(null)
  const canScan = typeof window !== 'undefined' && 'BarcodeDetector' in window

  async function refresh() {
    api.myStats().then(setStats).catch(() => {})
    listQueue().then((q) => setPending(q.length)).catch(() => {})
  }

  async function sync() {
    const q = await listQueue().catch(() => [])
    for (const item of q) {
      const fd = new FormData()
      Object.entries(item.fields).forEach(([k, v]) => fd.append(k, v))
      if (item.photo) fd.append('photo', new File([item.photo], 'bin.jpg', { type: 'image/jpeg' }))
      try { await api.submitPickup(fd); await removeFromQueue(item.id) } catch (e) {
        if (e instanceof TypeError) break // still offline, keep the rest
        await removeFromQueue(item.id)    // server rejected it: don't retry forever
        setMsg({ type: 'err', text: `Queued pickup rejected: ${e.message}` })
      }
    }
    refresh()
  }

  useEffect(() => {
    refresh(); sync()
    window.addEventListener('online', sync)
    return () => window.removeEventListener('online', sync)
  }, [])

  // Capture location when the screen opens (needs HTTPS or localhost)
  useEffect(() => {
    navigator.geolocation?.getCurrentPosition(
      (p) => setGps({ lat: p.coords.latitude, lon: p.coords.longitude }),
      () => setGps(null),
      { enableHighAccuracy: true, timeout: 8000 }
    )
  }, [])

  async function startScan() {
    setScanning(true)
    let stream
    try {
      stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
      videoRef.current.srcObject = stream
      await videoRef.current.play()
      const det = new window.BarcodeDetector({ formats: ['qr_code'] })
      let stop = false
      const tick = async () => {
        if (stop) return
        const codes = await det.detect(videoRef.current).catch(() => [])
        if (codes[0]) {
          stop = true
          stream.getTracks().forEach((t) => t.stop())
          setScanning(false)
          setQr(codes[0].rawValue)
          try { setBin(await api.getBin(codes[0].rawValue)) } catch (e) { setMsg({ type: 'err', text: e.message }) }
          return
        }
        requestAnimationFrame(tick)
      }
      tick()
    } catch {
      setScanning(false)
      setMsg({ type: 'err', text: 'Camera not available. Type the code instead.' })
    }
  }

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
    compress(f).then((small) => { setPhoto(small); setPreview(URL.createObjectURL(small)) })
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
      if (gps) { fd.append('latitude', gps.lat); fd.append('longitude', gps.lon) }
      if (photo) fd.append('photo', photo)
      try {
        await api.submitPickup(fd)
        setMsg({ type: 'ok', text: status === 'done' ? 'Pickup + photo submitted!' : 'Marked as missed' })
      } catch (err) {
        if (!(err instanceof TypeError)) throw err
        // No network: keep it on the phone, send automatically when back online.
        const fields = {}
        fd.forEach((v, k) => { if (k !== 'photo') fields[k] = v })
        await enqueue({ fields, photo: photo || null })
        setMsg({ type: 'ok', text: 'Offline: saved on this phone and will upload when the network returns.' })
      }
      refresh()
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
          {canScan && (
            <button className="btn btn-ok" onClick={startScan} disabled={scanning}>Scan QR with camera</button>
          )}
          {scanning && <video ref={videoRef} playsInline muted className="photo-preview" />}
          <button className="btn btn-primary" onClick={lookupBin} disabled={!qr.trim()}>
            Lookup Bin
          </button>
          <p style={{ fontSize: 11, color: '#718096', marginTop: 6 }}>
            Location: {gps ? `${gps.lat.toFixed(5)}, ${gps.lon.toFixed(5)}` : 'not captured (allow location, use HTTPS)'}
          </p>
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

        {stats && (
          <div className="card" style={{ fontSize: 13 }}>
            <strong>My record</strong>
            <div style={{ marginTop: 6 }}>
              Pickups done: {stats.done} · missed: {stats.missed}<br />
              Verified clean: {stats.verified_clean} · bonus: ₹{stats.bonus_rupees} (pilot rate ₹{stats.rate} per clean pickup)
              {pending > 0 && <><br /><strong>{pending} waiting to upload</strong> <button onClick={sync} style={{ marginLeft: 6 }}>Sync now</button></>}
            </div>
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
