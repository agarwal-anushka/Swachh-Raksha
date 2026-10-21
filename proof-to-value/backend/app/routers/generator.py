import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, auth
from ..services.geo import site_check
from ..services.rules import RULES, LADDER

router = APIRouter(prefix="/generator", tags=["generator"])
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
GEN = Depends(auth.require_role("generator"))


def _notice_out(n: models.Notice) -> dict:
    ev = n.evidence
    return {"id": n.id, "level": n.level, "status": n.status, "evidence_id": n.evidence_id,
            "photo_url": f"/generator/photo/{n.evidence_id}", "this_hash": ev.this_hash,
            "server_time": ev.server_time.isoformat(), "bin_label": ev.pickup.bin.label,
            "officer_remark": n.officer_remark, "contest_text": n.contest_text,
            "created_at": n.created_at.isoformat(),
            "issued_at": n.issued_at.isoformat() if n.issued_at else None,
            "generator_name": n.generator.name, "ladder_text": LADDER.get(n.level, n.level), "rules": RULES,
            **site_check(ev, n.generator)}


@router.get("/me")
def my_view(db: Session = Depends(get_db), user: models.User = GEN):
    gen = db.query(models.Generator).filter(models.Generator.id == user.generator_id).first()
    if not gen:
        raise HTTPException(404, "No generator linked to this account")
    # Generators only ever see notices an officer has acted on, never raw proposals.
    notices = (db.query(models.Notice)
               .filter(models.Notice.generator_id == gen.id, models.Notice.status != "proposed")
               .order_by(models.Notice.created_at.desc()).all())
    verdicts = (db.query(models.Verdict).join(models.Evidence).join(models.Pickup).join(models.Bin)
                .filter(models.Bin.generator_id == gen.id).all())
    return {
        "generator": {"id": gen.id, "name": gen.name, "type": gen.type},
        "summary": {"sorted": sum(v.final_verdict == "sorted" for v in verdicts),
                    "mixed": sum(v.final_verdict == "mixed" for v in verdicts),
                    "unclear": sum(v.final_verdict == "unclear" for v in verdicts)},
        "notices": [_notice_out(n) for n in notices],
    }


@router.get("/photo/{evidence_id}")
def my_photo(evidence_id: int, db: Session = Depends(get_db), user: models.User = GEN):
    n = (db.query(models.Notice).filter(models.Notice.evidence_id == evidence_id,
         models.Notice.generator_id == user.generator_id, models.Notice.status != "proposed").first())
    if not n:
        raise HTTPException(404, "Not available")
    return FileResponse(os.path.join(UPLOAD_DIR, n.evidence.photo_path), media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})


@router.post("/notices/{notice_id}/contest")
def contest(notice_id: int, payload: schemas.ContestIn, db: Session = Depends(get_db), user: models.User = GEN):
    n = db.query(models.Notice).filter(models.Notice.id == notice_id,
                                       models.Notice.generator_id == user.generator_id).first()
    if not n:
        raise HTTPException(404, "Notice not found")
    if n.status != "confirmed":
        raise HTTPException(400, f"Only an issued notice can be contested (this one is {n.status})")
    if not payload.text.strip():
        raise HTTPException(400, "Please explain why you are contesting")
    n.status, n.contest_text, n.contested_at = "contested", payload.text.strip(), datetime.utcnow()
    db.commit()
    return _notice_out(n)
