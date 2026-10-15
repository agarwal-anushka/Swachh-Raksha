from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/officer", tags=["officer"])


@router.get("/notices", response_model=List[schemas.NoticeOut])
def list_notices(
    status: str = None,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("officer", "admin")),
):
    q = db.query(models.Notice)
    if status:
        q = q.filter(models.Notice.status == status)
    return q.order_by(models.Notice.created_at.desc()).all()


@router.post("/notices/{notice_id}/action", response_model=schemas.NoticeOut)
def act_on_notice(
    notice_id: int,
    payload: schemas.NoticeAction,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("officer", "admin")),
):
    notice = db.query(models.Notice).filter(models.Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(404, "Notice not found")
    if notice.status != "proposed":
        raise HTTPException(400, f"Notice is already {notice.status}")

    if payload.action == "confirm":
        notice.status = "confirmed"
    elif payload.action == "dismiss":
        notice.status = "dismissed"
    else:
        raise HTTPException(400, "action must be confirm or dismiss")

    notice.officer_id = current_user.id
    notice.officer_remark = payload.remark
    notice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(notice)
    return notice


@router.get("/dashboard")
def dashboard_stats(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("officer", "admin")),
):
    total_evidence = db.query(models.Evidence).count()
    locked_verdicts = db.query(models.Verdict).count()
    pending_reviews = total_evidence - locked_verdicts
    proposed_notices = db.query(models.Notice).filter(models.Notice.status == "proposed").count()
    confirmed_notices = db.query(models.Notice).filter(models.Notice.status == "confirmed").count()
    mixed = db.query(models.Verdict).filter(models.Verdict.final_verdict == "mixed").count()
    sorted_ = db.query(models.Verdict).filter(models.Verdict.final_verdict == "sorted").count()

    return {
        "total_evidence": total_evidence,
        "locked_verdicts": locked_verdicts,
        "pending_reviews": pending_reviews,
        "proposed_notices": proposed_notices,
        "confirmed_notices": confirmed_notices,
        "verdict_breakdown": {"sorted": sorted_, "mixed": mixed},
    }
