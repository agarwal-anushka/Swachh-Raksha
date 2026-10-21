# Proof-to-Value: Pilot Prototype

Evidence system for segregation at Bulk Waste Generators (Gwalior Vigyan Mahotsav 2026).

## Run

```bash
# backend (Python 3.11+)
cd backend && python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
PTV_DEMO=1 uvicorn app.main:app --reload --host 0.0.0.0 --port 8000   # PTV_DEMO=1 enables the tamper demo buttons

# frontend (second terminal)
cd frontend && npm install && npm run demo     # builds and serves http://localhost:5173 (use this for phones: no live-reload, so the page never restarts mid-scan)
# for development with hot reload, use: npm run dev
```

Camera QR scan (any browser, via jsQR) and GPS need HTTPS or localhost (use `ngrok http 5173` for a phone).
Set `PTV_SECRET_KEY` for anything beyond a demo. The database is `backend/proof_to_value.db` (SQLite) and photos are in `backend/uploads/`; both are git-ignored.

## Logins

| Role | Email | Password |
|---|---|---|
| Admin | admin@ptv.local | admin123 |
| Collector | collector@ptv.local | collect123 |
| Reviewers 1-4 | reviewer1..4@ptv.local | review123 |
| Case officer | officer@ptv.local | officer123 |
| Generator (Hostel Block A) | generator@ptv.local | generator123 |

Pre-seeded: 3 campus generators (`PTV-2026-00001..00005`) and 12 fictional Gwalior-style generators (hotel, hospital, mall, school, mandi and so on) with a wet and dry bin each. Business names are invented and marked "(Demo)"; only the locality names are real. Admin page > *Open printable QR sheet* shows every code to print or scan from a screen.

To reset demo data, stop the server and delete `backend/proof_to_value.db`.

## Demo flow (about 3 minutes)

1. **Collector**: scan/enter `PTV-2026-00001`, photograph the open bin, submit (location is captured).
2. **Reviewers**: each reviewer is in a different zone and **never sees a generator in their own zone**. Hostel A is Zone-1, so use reviewers 2, 3, 4. Reviewers see only an EXIF-stripped photo: no owner, bin, stream or location.
3. After the third review the verdict **locks**. A clear majority of "mixed" proposes a notice (warning, then notice, then fine recommendation, counted per generator over 30 days). A 1-1-1 split is "unclear" and creates no notice.
4. **Officer**: identity, votes, history, original photo and hash are revealed only now. Confirm or dismiss. Missed city pickups are listed at the bottom.
5. **Generator**: sees the confirmed notice with its evidence and can **contest** it; the officer then upholds or withdraws.
6. **Tamper test** (officer page, needs `PTV_DEMO=1`): click *Verify chain* (green), *Demo: edit record #1*, *Verify chain* again (red, names the broken record), *Demo: restore*.

## Extra features

- **Hidden test photos:** Admin page, upload a photo with its known answer. It is mixed into every reviewer's queue (every 3rd slot) and looks identical to a real one. The officer page shows each reviewer's test accuracy and agreement with the final verdict.
- **Collector bonus:** shown to the collector and the officer. Only pickups whose verdict locked as "sorted" count (illustrative Rs 5 each; set `PTV_BONUS_PER_CLEAN`).
- **Offline queue + compression:** photos are shrunk on the phone (max 1600 px). With no network, a pickup is saved on the phone and uploaded on reconnect (or "Sync now"). The phone's capture time is kept; the server still stamps its own time.
- **Printable QR codes:** Admin page shows a QR image for every bin.
- **Monthly compliance pack:** officer page, CSV with one row per generator (pickups, verdicts, segregation rate, notices, contests).

## What is and is not built

Built: everything above plus QR + photo + GPS capture, SHA-256 chain over photo, bin, both timestamps and location (with verify), blind 3-reviewer majority, officer case view, generator view and contest, missed-pickup log, role-based access, authenticated photo access.

Not built (planned): SMS/WhatsApp notices, fine calculation and payment, Bio-Pod management, S3 storage. The pilot uses SQLite; the design targets PostgreSQL.

Known limits: the chain lock is per process (single server); the chain proves records were not altered after capture, not that the photo is of the right bin; the offline queue needs a browser with IndexedDB.
