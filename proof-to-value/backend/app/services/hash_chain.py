"""Tamper-evident evidence chain.

Every evidence row hashes ALL of its key fields plus the previous row's hash, so
changing a photo, the bin, the location, either timestamp or the order breaks
every hash after it. verify_chain() recomputes everything from the stored files.
"""
import hashlib
import os
import threading
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models

# One process, one chain head. Serialises "read latest hash -> insert" so two
# simultaneous uploads cannot both extend the same head. (prev_hash is also
# UNIQUE in the DB, so a fork would be rejected even if this lock were bypassed.)
CHAIN_LOCK = threading.Lock()


def compute_photo_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def _num(v) -> str:
    return "-" if v is None else f"{float(v):.7f}"


def _ts(v) -> str:
    return "-" if v is None else v.isoformat()


def compute_this_hash(photo_hash, pickup_id, bin_id, server_time, device_time,
                      latitude, longitude, prev_hash) -> str:
    payload = "|".join([
        photo_hash, str(pickup_id), str(bin_id), _ts(server_time), _ts(device_time),
        _num(latitude), _num(longitude), prev_hash or "GENESIS",
    ])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_latest_hash(db: Session) -> str | None:
    last = db.query(models.Evidence).order_by(models.Evidence.id.desc()).first()
    return last.this_hash if last else None


def verify_chain(db: Session, upload_dir: str) -> dict:
    """Recompute the whole chain from disk. Returns ok flag + first broken link."""
    rows = db.query(models.Evidence).order_by(models.Evidence.id.asc()).all()
    prev = None
    for ev in rows:
        def broken(reason):
            return {"ok": False, "checked": ev.id, "total": len(rows),
                    "broken_evidence_id": ev.id, "reason": reason, "head": None}
        path = os.path.join(upload_dir, ev.photo_path)
        if not os.path.exists(path):
            return broken("photo file is missing")
        with open(path, "rb") as f:
            if compute_photo_hash(f.read()) != ev.photo_hash:
                return broken("photo file was changed after capture")
        if (ev.prev_hash or None) != prev:
            return broken("link to previous record is broken (record removed or reordered)")
        expected = compute_this_hash(
            ev.photo_hash, ev.pickup_id, ev.pickup.bin_id, ev.server_time,
            ev.device_time, ev.latitude, ev.longitude, ev.prev_hash)
        if expected != ev.this_hash:
            return broken("record fields (bin, time or location) were changed")
        prev = ev.this_hash
    return {"ok": True, "total": len(rows), "head": prev, "broken_evidence_id": None, "reason": None}
