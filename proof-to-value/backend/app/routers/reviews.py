import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth
from ..services.verdict import try_lock_verdict
from ..services.photos import reviewer_copy

router = APIRouter(prefix="/reviews", tags=["reviews"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")


def _eligible(db: Session, ev: models.Evidence, user: models.User) -> bool:
    """Blind-review rules: not locked, <3 reviews, not already reviewed by me,
    and reviewer's zone differs from the generator's zone."""
    if db.query(models.Verdict).filter(models.Verdict.evidence_id == ev.id).first():
        return False
    reviews = db.query(models.Review).filter(models.Review.evidence_id == ev.id).all()
    if len(reviews) >= 3 or any(r.reviewer_id == user.id for r in reviews):
        return False
    gen = ev.pickup.bin.generator
    if gen and gen.zone and user.zone and gen.zone == user.zone:
        return False
    return True


@router.get("/queue", response_model=List[schemas.ReviewQueueItem])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("reviewer")),
):
    """Only evidence this reviewer may grade. No stream, no generator, no location."""
    evs = db.query(models.Evidence).order_by(models.Evidence.created_at.asc()).limit(200).all()
    return [
        schemas.ReviewQueueItem(
            evidence_id=ev.id,
            photo_url=f"/reviews/photo/{ev.id}",
            created_at=ev.created_at,
        )
        for ev in evs if _eligible(db, ev, current_user)
    ]


@router.get("/photo/{evidence_id}")
def reviewer_photo(
    evidence_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("reviewer")),
):
    """Authenticated, EXIF-stripped, downsized copy. Never the original file."""
    ev = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not ev or not _eligible(db, ev, current_user):
        raise HTTPException(404, "Not available")
    with open(os.path.join(UPLOAD_DIR, ev.photo_path), "rb") as f:
        data = reviewer_copy(f.read())
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/", response_model=schemas.ReviewOut)
def submit_review(
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("reviewer")),
):
    if payload.verdict not in ("sorted", "mixed", "unclear"):
        raise HTTPException(400, "verdict must be sorted, mixed or unclear")

    evidence = db.query(models.Evidence).filter(models.Evidence.id == payload.evidence_id).first()
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    if db.query(models.Verdict).filter(models.Verdict.evidence_id == payload.evidence_id).first():
        raise HTTPException(400, "Verdict already locked")
    if not _eligible(db, evidence, current_user):
        raise HTTPException(403, "You cannot review this item")

    review = models.Review(evidence_id=payload.evidence_id, reviewer_id=current_user.id, verdict=payload.verdict)
    db.add(review)
    db.commit()
    db.refresh(review)

    try_lock_verdict(db, payload.evidence_id)  # locks on the 3rd review
    return review
