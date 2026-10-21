import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'

function Tag({ b }) {
  const [src, setSrc] = useState(null)
  useEffect(() => { api.qrBlob(b.id).then(setSrc).catch(() => {}) }, [b.id])
  return (
    <div className="qr-tag">
      {src ? <img src={src} alt={b.qr_code} /> : <div style={{ height: 140 }} />}
      <strong>{b.generator_name}</strong>
      <span>{b.stream.toUpperCase()} bin</span>
      <code>{b.qr_code}</code>
    </div>
  )
}

// Printable sheet of every bin's QR code. Print it, or show it on a screen and scan from the collector page.
export default function QrSheet() {
  const nav = useNavigate()
  const [bins, setBins] = useState([])
  useEffect(() => { api.listBins().then(setBins).catch(() => {}) }, [])
  return (
    <div style={{ padding: 16 }}>
      <div className="no-print" style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <button className="btn btn-outline" onClick={() => nav('/admin')}>Back</button>
        <button className="btn btn-primary" onClick={() => window.print()}>Print</button>
      </div>
      <div className="qr-grid">{bins.map((b) => <Tag key={b.id} b={b} />)}</div>
      <style>{`
        .qr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); gap: 12px; }
        .qr-tag { border: 1px dashed #999; border-radius: 8px; padding: 10px; text-align: center; font-size: 12px; display: flex; flex-direction: column; gap: 2px; break-inside: avoid; background: #fff; }
        .qr-tag img { width: 100%; max-width: 160px; margin: 0 auto; }
        @media print { .no-print { display: none !important; } body { background: #fff; } }
      `}</style>
    </div>
  )
}
