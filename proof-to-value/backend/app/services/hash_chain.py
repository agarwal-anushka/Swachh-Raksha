import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from .. import models


def compute_photo_hash(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()


def compute_this_hash(photo_hash: str, server_time: datetime, prev_hash: str | None) -> str:
    prev = prev_hash or "GENESIS"
    payload = f"{photo_hash}|{server_time.isoformat()}|{prev}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def get_latest_hash(db: Session) -> str | None:
    last = (
        db.query(models.Evidence)
        .order_by(models.Evidence.id.desc())
        .first()
    )
    return last.this_hash if last else None
