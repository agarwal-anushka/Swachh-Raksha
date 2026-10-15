import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, getUser, clearAuth } from '../api/client'

export default function Admin() {
  const user = getUser()
  const nav = useNavigate()
  const [gens, setGens] = useState([])
  const [bins, setBins] = useState([])
  const [msg, setMsg] = useState(null)
  const [genForm, setGenForm] = useState({ name: '', type: 'hostel' })
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
      setGenForm({ name: '', type: 'hostel' })
      load()
    } catch (err) {
      setMsg({ type: 'err', text: err.message })
    }
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
          <h3>Bins ({bins.length})</h3>
          {bins.map((b) => (
            <div key={b.id} style={{ padding: '8px 0', borderBottom: '1px solid #e2e8f0', fontSize: 13 }}>
              <strong style={{ fontFamily: 'monospace' }}>{b.qr_code}</strong>
              <div style={{ color: '#4A5568' }}>{b.generator_name} · {b.stream}</div>
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
