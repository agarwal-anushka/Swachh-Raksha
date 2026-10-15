from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth
from ..services.verdict import try_lock_verdict

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.get("/queue", response_model=List[schemas.ReviewQueueItem])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("reviewer", "admin")),
):
    """Return evidence that still needs reviews (less than 3) and not yet reviewed by me."""
    # Evidence without a locked verdict
    locked_ids = db.query(models.Verdict.evidence_id).subquery()
    evidence_list = (
        db.query(models.Evidence)
        .filter(~models.Evidence.id.in_(locked_ids))
        .order_by(models.Evidence.created_at.asc())
        .limit(50)
        .all()
    )

    result = []
    for ev in evidence_list:
        my_review = (
            db.query(models.Review)
            .filter(models.Review.evidence_id == ev.id, models.Review.reviewer_id == current_user.id)
            .first()
        )
        review_count = db.query(models.Review).filter(models.Review.evidence_id == ev.id).count()
        if review_count >= 3:
            continue
        if my_review:
            continue  # already reviewed by this user

        stream = ev.pickup.bin.stream if ev.pickup and ev.pickup.bin else "unknown"
        result.append(schemas.ReviewQueueItem(
            evidence_id=ev.id,
            photo_url=f"/uploads/{ev.photo_path}",
            stream=stream,
            created_at=ev.created_at,
            already_reviewed_by_me=False,
        ))
    return result


@router.post("/", response_model=schemas.ReviewOut)
def submit_review(
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("reviewer", "admin")),
):
    if payload.verdict not in ("sorted", "mixed", "unclear"):
        raise HTTPException(400, "verdict must be sorted, mixed or unclear")

    evidence = db.query(models.Evidence).filter(models.Evidence.id == payload.evidence_id).first()
    if not evidence:
        raise HTTPException(404, "Evidence not found")

    # Already locked?
    if db.query(models.Verdict).filter(models.Verdict.evidence_id == payload.evidence_id).first():
        raise HTTPException(400, "Verdict already locked")

    # Already reviewed by this user?
    existing = (
        db.query(models.Review)
        .filter(models.Review.evidence_id == payload.evidence_id, models.Review.reviewer_id == current_user.id)
        .first()
    )
    if existing:
        raise HTTPException(400, "You already reviewed this evidence")

    review = models.Review(
        evidence_id=payload.evidence_id,
        reviewer_id=current_user.id,
        verdict=payload.verdict,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    # Try to lock if we now have 3 reviews
    try_lock_verdict(db, payload.evidence_id)

    return review


@router.get("/verdict/{evidence_id}", response_model=schemas.VerdictOut)
def get_verdict(
    evidence_id: int,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.get_current_user),
):
    verdict = db.query(models.Verdict).filter(models.Verdict.evidence_id == evidence_id).first()
    if not verdict:
        raise HTTPException(404, "Verdict not yet locked")
    return verdict
