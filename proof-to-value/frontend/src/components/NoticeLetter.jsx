import { useState, useEffect } from 'react'
import { api } from '../api/client'

export function siteLine(n) {
  const d = n.site_distance_m
  if (n.site_status === 'at_site') return { ok: true, text: `Captured ${d} m from the registered site` }
  if (n.site_status === 'near') return { ok: false, text: `Captured ${d} m from the registered site: check` }
  if (n.site_status === 'far') return { ok: false, text: `Captured ${d} m from the registered site: FAR, review before acting` }
  if (n.site_status === 'no_gps') return { ok: false, text: 'No GPS on this photo' }
  return { ok: false, text: 'Site location not registered yet' }
}

export function RulesBox({ rules }) {
  if (!rules) return null
  return (
    <details style={{ fontSize: 12, margin: '8px 0', background: '#EDF2F7', borderRadius: 8, padding: '6px 10px' }}>
      <summary style={{ cursor: 'pointer', fontWeight: 600 }}>Legal basis and limits</summary>
      <p style={{ margin: '6px 0' }}>{rules.basis}</p>
      <p style={{ margin: '6px 0' }}>{rules.fine_note}</p>
      <p style={{ margin: '6px 0' }}><strong>Limit:</strong> {rules.not_proof}</p>
    </details>
  )
}

// A printable notice: the evidence, the rule it rests on, and the right to contest.
export default function NoticeLetter({ n, photoUrl }) {
  const [open, setOpen] = useState(false)
  const [src, setSrc] = useState(null)
  useEffect(() => { if (open && photoUrl) api.photoBlob(photoUrl).then(setSrc).catch(() => {}) }, [open, photoUrl])
  const site = siteLine(n)
  return (
    <>
      <button className="btn btn-outline no-print" style={{ padding: 8, marginTop: 8 }} onClick={() => setOpen(!open)}>
        {open ? 'Hide notice letter' : 'View / print notice letter'}
      </button>
      {open && (
        <div className="letter">
          <h2 style={{ fontSize: 16, marginBottom: 2 }}>NOTICE OF NON-SEGREGATION: {n.level.replace('_', ' ').toUpperCase()}</h2>
          <p style={{ fontSize: 11, color: '#4A5568', marginBottom: 8 }}>Pilot prototype notice. Issued {n.issued_at ? new Date(n.issued_at).toLocaleString() : 'on confirmation'}</p>
          <p style={{ fontSize: 13 }}><strong>To:</strong> {n.generator_name}</p>
          <p style={{ fontSize: 13 }}><strong>Stage:</strong> {n.ladder_text}</p>
          <p style={{ fontSize: 13 }}><strong>Evidence:</strong> {n.bin_label}, photographed {new Date(n.server_time).toLocaleString()}</p>
          <p style={{ fontSize: 13 }}><strong>Place check:</strong> {site.text}</p>
          {src && <img src={src} alt="evidence" style={{ width: '100%', maxWidth: 360, margin: '8px 0', borderRadius: 6 }} />}
          <p style={{ fontSize: 10, wordBreak: 'break-all', color: '#4A5568' }}>Evidence hash (SHA-256 chain): {n.this_hash}</p>
          {n.officer_remark && <p style={{ fontSize: 13 }}><strong>Officer remark:</strong> {n.officer_remark}</p>}
          <p style={{ fontSize: 12, marginTop: 8 }}>{n.rules?.basis}</p>
          <p style={{ fontSize: 12 }}>{n.rules?.fine_note}</p>
          <p style={{ fontSize: 12 }}><strong>Right to contest:</strong> you may contest this notice with your reason from your Proof-to-Value login. Contested notices are reviewed by a case officer.</p>
          <button className="btn btn-primary no-print" style={{ marginTop: 8 }} onClick={() => window.print()}>Print / Save as PDF</button>
        </div>
      )}
      <style>{`
        .letter { border: 1px solid #cbd5e0; border-radius: 8px; padding: 14px; margin-top: 8px; background: #fff; }
        @media print {
          body * { visibility: hidden; }
          .letter, .letter * { visibility: visible; }
          .letter { position: absolute; left: 0; top: 0; width: 100%; border: none; }
          .no-print { display: none !important; }
        }
      `}</style>
    </>
  )
}
