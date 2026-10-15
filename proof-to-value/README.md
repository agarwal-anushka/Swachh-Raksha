# Proof-to-Value – Pilot Prototype

Evidence-based waste segregation system for Gwalior Bulk Waste Generators.

## Quick Start (Backend)

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open: http://localhost:8000/docs

## Default Login Credentials

| Role       | Email                  | Password    |
|------------|------------------------|-------------|
| Admin      | admin@ptv.local        | admin123    |
| Collector  | collector@ptv.local    | collect123  |
| Reviewer 1 | reviewer1@ptv.local    | review123   |
| Reviewer 2 | reviewer2@ptv.local    | review123   |
| Reviewer 3 | reviewer3@ptv.local    | review123   |
| Officer    | officer@ptv.local      | officer123  |

## Sample QR Codes (pre-seeded)

- `PTV-2026-00001` → Hostel Block A – Wet
- `PTV-2026-00002` → Hostel Block A – Dry
- `PTV-2026-00003` → Central Mess – Wet
- `PTV-2026-00004` → Central Mess – Dry
- `PTV-2026-00005` → Academic Block C – Wet

## Demo Flow

1. Login as **collector** → submit pickup with photo for a QR
2. Login as **reviewer1 / reviewer2 / reviewer3** → grade the photo
3. After 3 reviews → verdict locks automatically
4. Login as **officer** → see proposed notices and confirm/dismiss
5. Login as **admin** → manage generators, bins, users

## Tech Stack

- FastAPI + SQLAlchemy + SQLite
- JWT Auth
- SHA-256 hash chain for evidence
- 3-reviewer majority verdict locking
