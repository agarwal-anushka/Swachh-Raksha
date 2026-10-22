import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getUser, clearAuth } from '../api/client'

export default function Admin() {
  const user = getUser()
  const nav = useNavigate()
  const [gens, setGens] = useState([])
  const [bins, setBins] = useState([])
  const [msg, setMsg] = useState(null)
  const [genForm, setGenForm] = useState({ name: '', type: 'hostel', zone: '' })
  const [binForm, setBinForm] = useState({ generator_id: '', stream: 'wet', label: '' })

  async function load() {
    try {
      const [g, b] = await Promise.all([api.listGenerators(), api.listBins()])
      setGens(g)
      setBins(b)
    } catch (e) {
      setMsg({ type: 'err', text: e.message })
    }
  }

  useEffect(() => { load() }, [])

  async function addGen(e) {
    e.preventDefault()
    try {
      await api.createGenerator(genForm)
      setMsg({ type: 'ok', text: 'Generator created' })
      setGenForm({ name: '', type: 'hostel', zone: '' })
      load()
    } catch (err) {
      setMsg({ type: 'err', text: err.message })
    }
  }

  const [tests, setTests] = useState([])
  const [testForm, setTestForm] = useState({ expected: 'mixed', file: null })
  useEffect(() => { api.listTestPhotos().then(setTests).catch(() => {}) }, [])

  async function addTest(e) {
    e.preventDefault()
    try {
      const fd = new FormData()
      fd.append('expected', testForm.expected)
      fd.append('photo', testForm.file)
      await api.addTestPhoto(fd)
      setMsg({ type: 'ok', text: 'Test photo added. It will appear in reviewers\' queues like any other.' })
      setTests(await api.listTestPhotos())
    } catch (err) { setMsg({ type: 'err', text: err.message }) }
  }

  async function addBin(e) {
    e.preventDefault()
    try {
      const created = await api.createBin({
        ...binForm,
        generator_id: Number(binForm.generator_id),
      })
      setMsg({ type: 'ok', text: `Bin created — QR: ${created.qr_code}` })
      setBinForm({ generator_id: '', stream: 'wet', label: '' })
      load()
    } catch (err) {
      setMsg({ type: 'err', text: err.message })
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
          <div className="role">{user?.name} · Admin</div>
        </div>
        <button onClick={logout}>Logout</button>
      </div>

      <div className="content">
        {msg && <div className={`msg msg-${msg.type}`}>{msg.text}</div>}

        <div className="card">
          <h3>Add Generator</h3>
          <form onSubmit={addGen}>
            <input placeholder="Name" value={genForm.name} onChange={(e) => setGenForm({ ...genForm, name: e.target.value })} required />
            <select value={genForm.type} onChange={(e) => setGenForm({ ...genForm, type: e.target.value })}>
              <option value="hostel">Hostel</option>
              <option value="mess">Mess</option>
              <option value="academic">Academic</option>
              <option value="other">Other</option>
            </select>
            <input placeholder="Zone (e.g. Zone-1): reviewers in this zone never see its photos" value={genForm.zone} onChange={(e) => setGenForm({ ...genForm, zone: e.target.value })} />
            <button className="btn btn-primary">Create Generator</button>
          </form>
        </div>

        <div className="card">
          <h3>Add Bin</h3>
          <form onSubmit={addBin}>
            <select value={binForm.generator_id} onChange={(e) => setBinForm({ ...binForm, generator_id: e.target.value })} required>
              <option value="">Select generator</option>
              {gens.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}
            </select>
            <select value={binForm.stream} onChange={(e) => setBinForm({ ...binForm, stream: e.target.value })}>
              <option value="wet">Wet</option>
              <option value="dry">Dry</option>
              <option value="sanitary">Sanitary</option>
              <option value="special">Special</option>
            </select>
            <input placeholder="Label (optional)" value={binForm.label} onChange={(e) => setBinForm({ ...binForm, label: e.target.value })} />
            <button className="btn btn-primary">Create Bin + QR</button>
          </form>
        </div>

        <div className="card">
          <h3>Registered site locations</h3>
          <p style={{ fontSize: 12, color: '#4A5568', marginBottom: 8 }}>
            Each photo is compared with its generator's registered point. Stand at the bins and press "Use my location", or type coordinates.
          </p>
          {gens.map((g) => <SiteRow key={g.id} g={g} onSaved={load} />)}
        </div>

        <div className="card">
          <h3>Hidden test photos ({tests.length})</h3>
          <p style={{ fontSize: 12, color: '#4A5568', marginBottom: 8 }}>Known-answer photos silently mixed into reviewers' queues to measure reviewer quality.</p>
          <form onSubmit={addTest}>
            <select value={testForm.expected} onChange={(e) => setTestForm({ ...testForm, expected: e.target.value })}>
              <option value="mixed">Correct answer: Mixed</option>
              <option value="sorted">Correct answer: Sorted</option>
            </select>
            <input type="file" accept="image/*" onChange={(e) => setTestForm({ ...testForm, file: e.target.files[0] })} required />
            <button className="btn btn-primary">Add test photo</button>
          </form>
        </div>

        <div className="card">
          <h3>Bins ({bins.length})</h3>
          <button className="btn btn-primary" onClick={() => nav('/qr-sheet')}>Open printable QR sheet</button>
          {bins.map((b) => (
            <div key={b.id} style={{ padding: '8px 0', borderBottom: '1px solid #e2e8f0', fontSize: 13 }}>
              <strong style={{ fontFamily: 'monospace' }}>{b.qr_code}</strong>
              <div style={{ color: '#4A5568' }}>{b.generator_name} · {b.stream}</div>
              <QR id={b.id} />
            </div>
          ))}
        </div>

        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button className="btn btn-outline" onClick={() => nav('/collector')}>Collector view</button>
          <button className="btn btn-outline" onClick={() => nav('/reviewer')}>Reviewer view</button>
          <button className="btn btn-outline" onClick={() => nav('/officer')}>Officer view</button>
        </div>
      </div>
    </div>
  )
}

function QR({ id }) {
  const [src, setSrc] = useState(null)
  useEffect(() => { api.qrBlob(id).then(setSrc).catch(() => {}) }, [id])
  return src ? <img src={src} alt="QR" style={{ width: 96, height: 96, marginTop: 6 }} /> : null
}

function SiteRow({ g, onSaved }) {
  const [lat, setLat] = useState(g.latitude ?? '')
  const [lon, setLon] = useState(g.longitude ?? '')
  const [note, setNote] = useState(null) // result shown right next to the buttons, not at the top of the page

  function here() {
    setNote({ ok: true, text: 'Getting location…' })
    if (!navigator.geolocation) return setNote({ ok: false, text: 'This browser has no location support.' })
    navigator.geolocation.getCurrentPosition(
      (p) => { setLat(p.coords.latitude.toFixed(6)); setLon(p.coords.longitude.toFixed(6)); setNote({ ok: true, text: 'Got it. Now press Save.' }) },
      () => setNote({ ok: false, text: 'Location blocked. Use localhost or https, allow location, or type the numbers.' }),
      { enableHighAccuracy: true, timeout: 10000 }
    )
  }

  async function save() {
    const la = parseFloat(lat), lo = parseFloat(lon)
    if (lat === '' || lon === '' || Number.isNaN(la) || Number.isNaN(lo)) return setNote({ ok: false, text: 'Enter both latitude and longitude (numbers).' })
    if (Math.abs(la) > 90 || Math.abs(lo) > 180) return setNote({ ok: false, text: 'Coordinates out of range.' })
    try {
      await api.setLocation(g.id, la, lo)
      setNote({ ok: true, text: `Saved ✔ (${la.toFixed(5)}, ${lo.toFixed(5)})` })
      onSaved()
    } catch (e) { setNote({ ok: false, text: e.message }) }
  }

  return (
    <div style={{ padding: '8px 0', borderBottom: '1px solid #e2e8f0', fontSize: 12 }}>
      <strong>{g.name}</strong>
      <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
        <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder="lat" style={{ width: '30%' }} />
        <input value={lon} onChange={(e) => setLon(e.target.value)} placeholder="lon" style={{ width: '30%' }} />
        <button onClick={here}>Use my location</button>
        <button onClick={save}>Save</button>
      </div>
      {note && <div style={{ marginTop: 4, fontWeight: 600, color: note.ok ? '#276749' : '#C53030' }}>{note.text}</div>}
    </div>
  )
}
