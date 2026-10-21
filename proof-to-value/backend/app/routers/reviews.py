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


def _parse(ref: str):
    if len(ref) < 2 or ref[0] not in "et" or not ref[1:].isdigit():
        raise HTTPException(400, "Bad reference")
    return ref[0], int(ref[1:])


def _open_tests(db: Session, user: models.User):
    answered = db.query(models.TestResponse.test_id).filter(models.TestResponse.reviewer_id == user.id)
    return db.query(models.TestPhoto).filter(~models.TestPhoto.id.in_(answered)).order_by(models.TestPhoto.id).all()


@router.get("/queue", response_model=List[schemas.ReviewQueueItem])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("reviewer")),
):
    """Only items this reviewer may grade, with hidden test photos mixed in (every 3rd slot).
    No stream, no generator, no location, and nothing that distinguishes a test photo."""
    evs = db.query(models.Evidence).order_by(models.Evidence.created_at.asc()).limit(200).all()
    items = [schemas.ReviewQueueItem(ref=f"e{ev.id}", photo_url=f"/reviews/photo/e{ev.id}", created_at=ev.created_at)
             for ev in evs if _eligible(db, ev, current_user)]
    for i, t in enumerate(_open_tests(db, current_user)):
        item = schemas.ReviewQueueItem(ref=f"t{t.id}", photo_url=f"/reviews/photo/t{t.id}", created_at=t.created_at)
        items.insert(min(2 + 3 * i, len(items)), item)
    return items


@router.get("/photo/{ref}")
def reviewer_photo(
    ref: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("reviewer")),
):
    """Authenticated, EXIF-stripped, downsized copy. Never the original file."""
    kind, ident = _parse(ref)
    if kind == "e":
        ev = db.query(models.Evidence).filter(models.Evidence.id == ident).first()
        if not ev or not _eligible(db, ev, current_user):
            raise HTTPException(404, "Not available")
        path = ev.photo_path
    else:
        t = db.query(models.TestPhoto).filter(models.TestPhoto.id == ident).first()
        if not t or t not in _open_tests(db, current_user):
            raise HTTPException(404, "Not available")
        path = t.photo_path
    with open(os.path.join(UPLOAD_DIR, path), "rb") as f:
        data = reviewer_copy(f.read())
    return Response(content=data, media_type="image/jpeg", headers={"Cache-Control": "no-store"})


@router.post("/")
def submit_review(
    payload: schemas.ReviewCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("reviewer")),
):
    if payload.verdict not in ("sorted", "mixed", "unclear"):
        raise HTTPException(400, "verdict must be sorted, mixed or unclear")
    kind, ident = _parse(payload.ref)

    if kind == "t":  # hidden test photo: score it, same response as a real review
        t = db.query(models.TestPhoto).filter(models.TestPhoto.id == ident).first()
        if not t or t not in _open_tests(db, current_user):
            raise HTTPException(404, "Not available")
        db.add(models.TestResponse(test_id=t.id, reviewer_id=current_user.id,
                                   verdict=payload.verdict, correct=payload.verdict == t.expected))
        db.commit()
        return {"ok": True}

    evidence = db.query(models.Evidence).filter(models.Evidence.id == ident).first()
    if not evidence:
        raise HTTPException(404, "Evidence not found")
    if db.query(models.Verdict).filter(models.Verdict.evidence_id == ident).first():
        raise HTTPException(400, "Verdict already locked")
    if not _eligible(db, evidence, current_user):
        raise HTTPException(403, "You cannot review this item")

    db.add(models.Review(evidence_id=ident, reviewer_id=current_user.id, verdict=payload.verdict))
    db.commit()
    try_lock_verdict(db, ident)  # locks on the 3rd review
    return {"ok": True}
