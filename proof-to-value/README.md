# Proof-to-Value: Pilot Prototype

Evidence system for segregation at Bulk Waste Generators (Gwalior Vigyan Mahotsav 2026).

## Run

```bash
# backend (Python 3.11+)
cd backend && python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
PTV_DEMO=1 uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # PTV_DEMO=1 enables the tamper demo buttons

# frontend (second terminal)
cd frontend && npm install && npm run dev      # http://localhost:5173
```

Camera QR scan and GPS need HTTPS or localhost (use `ngrok http 5173` for a phone).
Set `PTV_SECRET_KEY` for anything beyond a demo. The database is `backend/proof_to_value.db` (SQLite) and photos are in `backend/uploads/`; both are git-ignored.

## Logins

| Role | Email | Password |
|---|---|---|
| Admin | admin@ptv.local | admin123 |
| Collector | collector@ptv.local | collect123 |
| Reviewers 1-4 | reviewer1..4@ptv.local | review123 |
| Case officer | officer@ptv.local | officer123 |
| Generator (Hostel Block A) | generator@ptv.local | generator123 |

Pre-seeded QR codes: `PTV-2026-00001..00005` (Hostel A wet/dry, Mess wet/dry, Academic C wet).

## Demo flow (about 3 minutes)

1. **Collector**: scan/enter `PTV-2026-00001`, photograph the open bin, submit (location is captured).
2. **Reviewers**: each reviewer is in a different zone and **never sees a generator in their own zone**. Hostel A is Zone-1, so use reviewers 2, 3, 4. Reviewers see only an EXIF-stripped photo: no owner, bin, stream or location.
3. After the third review the verdict **locks**. A clear majority of "mixed" proposes a notice (warning, then notice, then fine recommendation, counted per generator over 30 days). A 1-1-1 split is "unclear" and creates no notice.
4. **Officer**: identity, votes, history, original photo and hash are revealed only now. Confirm or dismiss. Missed city pickups are listed at the bottom.
5. **Generator**: sees the confirmed notice with its evidence and can **contest** it; the officer then upholds or withdraws.
6. **Tamper test** (officer page, needs `PTV_DEMO=1`): click *Verify chain* (green), *Demo: edit record #1*, *Verify chain* again (red, names the broken record), *Demo: restore*.

## What is and is not built

Built: QR + photo + GPS capture, SHA-256 chain over photo, bin, both timestamps and location (with verify), blind 3-reviewer majority, officer case view, generator view and contest, missed-pickup log, role-based access, authenticated photo access.

Not built (planned): hidden test photos, offline queue, on-device compression, S3 storage, collector bonus, SMS/WhatsApp notices, fine calculation, Bio-Pod management. The pilot uses SQLite; the design targets PostgreSQL.

Known limits: the chain lock is per process (single server); the chain proves records were not altered after capture, not that the photo is of the right bin.
