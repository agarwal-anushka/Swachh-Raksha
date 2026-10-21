import os
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, auth
from ..services.hash_chain import verify_chain
from ..services.verdict import mixed_in_window

router = APIRouter(prefix="/officer", tags=["officer"])
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
DEMO = os.getenv("PTV_DEMO") == "1"
_ORIGINAL = {}  # evidence_id -> original latitude, for demo restore

OFFICER = Depends(auth.require_role("officer", "admin"))


def case_view(db: Session, n: models.Notice) -> dict:
    """Identity is revealed here, i.e. only AFTER the verdict has locked."""
    ev, gen = n.evidence, n.generator
    v = ev.verdict if ev else None
    pickup = ev.pickup if ev else None
    return {
        "id": n.id, "level": n.level, "status": n.status,
        "generator_id": n.generator_id, "generator_name": gen.name if gen else None,
        "generator_type": gen.type if gen else None,
        "bin_label": pickup.bin.label if pickup else None,
        "stream": pickup.bin.stream if pickup else None,
        "evidence_id": n.evidence_id,
        "photo_url": f"/officer/photo/{n.evidence_id}" if ev else None,
        "this_hash": ev.this_hash if ev else None,
        "server_time": ev.server_time.isoformat() if ev else None,
        "latitude": float(ev.latitude) if ev and ev.latitude is not None else None,
        "longitude": float(ev.longitude) if ev and ev.longitude is not None else None,
        "votes": {"sorted": v.sorted_count, "mixed": v.mixed_count, "unclear": v.unclear_count} if v else None,
        "mixed_last_30_days": mixed_in_window(db, n.generator_id),
        "mixed_all_time": db.query(models.Verdict).join(models.Evidence).join(models.Pickup).join(models.Bin)
            .filter(models.Bin.generator_id == n.generator_id, models.Verdict.final_verdict == "mixed").count(),
        "officer_remark": n.officer_remark, "contest_text": n.contest_text,
        "created_at": n.created_at.isoformat(),
    }


@router.get("/notices")
def list_notices(status: str = None, db: Session = Depends(get_db), _: models.User = OFFICER):
    q = db.query(models.Notice)
    if status:
        q = q.filter(models.Notice.status == status)
    return [case_view(db, n) for n in q.order_by(models.Notice.created_at.desc()).all()]


@router.get("/photo/{evidence_id}")
def original_photo(evidence_id: int, db: Session = Depends(get_db), _: models.User = OFFICER):
    ev = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not ev or not ev.verdict:  # photo is released to officers only after lock
        raise HTTPException(404, "Not available")
    return FileResponse(os.path.join(UPLOAD_DIR, ev.photo_path), media_type="image/jpeg",
                        headers={"Cache-Control": "no-store"})


ACTIONS = {
    "proposed": {"confirm": "confirmed", "dismiss": "dismissed"},
    "contested": {"uphold": "upheld", "withdraw": "withdrawn"},
}


@router.post("/notices/{notice_id}/action")
def act_on_notice(notice_id: int, payload: schemas.NoticeAction, db: Session = Depends(get_db),
                  current_user: models.User = OFFICER):
    notice = db.query(models.Notice).filter(models.Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(404, "Notice not found")
    allowed = ACTIONS.get(notice.status, {})
    if payload.action not in allowed:
        raise HTTPException(400, f"Cannot '{payload.action}' a notice that is {notice.status}")
    notice.status = allowed[payload.action]
    notice.officer_id = current_user.id
    notice.officer_remark = payload.remark or notice.officer_remark
    notice.updated_at = datetime.utcnow()
    db.commit()
    return case_view(db, notice)


@router.get("/missed")
def missed_pickups(db: Session = Depends(get_db), _: models.User = OFFICER):
    """Pickups the city side marked as missed (accountability log)."""
    rows = db.query(models.Pickup).filter(models.Pickup.status == "missed").order_by(models.Pickup.created_at.desc()).limit(50).all()
    return [{"id": p.id, "bin_label": p.bin.label, "generator_name": p.bin.generator.name,
             "reason": p.missed_reason, "at": p.created_at.isoformat()} for p in rows]


@router.get("/chain/verify")
def chain_verify(db: Session = Depends(get_db), _: models.User = OFFICER):
    return verify_chain(db, UPLOAD_DIR)


@router.get("/dashboard")
def dashboard_stats(db: Session = Depends(get_db), _: models.User = OFFICER):
    total_evidence = db.query(models.Evidence).count()
    locked = db.query(models.Verdict).count()
    count = lambda st: db.query(models.Notice).filter(models.Notice.status == st).count()
    vb = lambda v: db.query(models.Verdict).filter(models.Verdict.final_verdict == v).count()
    return {
        "total_evidence": total_evidence, "locked_verdicts": locked,
        "pending_reviews": total_evidence - locked,
        "proposed_notices": count("proposed"), "confirmed_notices": count("confirmed"),
        "contested_notices": count("contested"),
        "missed_pickups": db.query(models.Pickup).filter(models.Pickup.status == "missed").count(),
        "verdict_breakdown": {"sorted": vb("sorted"), "mixed": vb("mixed"), "unclear": vb("unclear")},
        "demo": DEMO,
    }


# ---- demo-only: simulate someone editing the database by hand (PTV_DEMO=1) ----
@router.post("/demo/tamper/{evidence_id}")
def demo_tamper(evidence_id: int, db: Session = Depends(get_db), _: models.User = OFFICER):
    if not DEMO:
        raise HTTPException(404, "Not found")
    ev = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not ev:
        raise HTTPException(404, "Evidence not found")
    _ORIGINAL[evidence_id] = ev.latitude
    ev.latitude = (float(ev.latitude) if ev.latitude is not None else 26.2183) + 0.01
    db.commit()
    return {"tampered": evidence_id}


@router.post("/demo/restore")
def demo_restore(db: Session = Depends(get_db), _: models.User = OFFICER):
    if not DEMO:
        raise HTTPException(404, "Not found")
    for eid, lat in list(_ORIGINAL.items()):
        ev = db.query(models.Evidence).filter(models.Evidence.id == eid).first()
        if ev:
            ev.latitude = lat
    _ORIGINAL.clear()
    db.commit()
    return {"restored": True}


BONUS_PER_CLEAN = int(os.getenv("PTV_BONUS_PER_CLEAN", "5"))  # rupees; illustrative pilot setting


def collector_stats(db: Session, collector_id: int) -> dict:
    pk = db.query(models.Pickup).filter(models.Pickup.collector_id == collector_id)
    clean = (db.query(models.Verdict).join(models.Evidence).join(models.Pickup)
             .filter(models.Pickup.collector_id == collector_id, models.Verdict.final_verdict == "sorted").count())
    return {"done": pk.filter(models.Pickup.status == "done").count(),
            "missed": pk.filter(models.Pickup.status == "missed").count(),
            "verified_clean": clean, "bonus_rupees": clean * BONUS_PER_CLEAN, "rate": BONUS_PER_CLEAN}


@router.get("/collectors")
def collectors(db: Session = Depends(get_db), _: models.User = OFFICER):
    return [{"name": u.name, **collector_stats(db, u.id)}
            for u in db.query(models.User).filter(models.User.role == "collector").all()]


@router.get("/reviewers")
def reviewers(db: Session = Depends(get_db), _: models.User = OFFICER):
    """Reviewer quality from hidden test photos, plus agreement with the final majority."""
    out = []
    for u in db.query(models.User).filter(models.User.role == "reviewer").all():
        tests = db.query(models.TestResponse).filter(models.TestResponse.reviewer_id == u.id).all()
        mine = (db.query(models.Review, models.Verdict)
                .join(models.Verdict, models.Verdict.evidence_id == models.Review.evidence_id)
                .filter(models.Review.reviewer_id == u.id).all())
        agree = sum(r.verdict == v.final_verdict for r, v in mine)
        out.append({"name": u.name, "zone": u.zone, "tests_answered": len(tests),
                    "tests_correct": sum(t.correct for t in tests),
                    "test_accuracy": round(100 * sum(t.correct for t in tests) / len(tests)) if tests else None,
                    "graded": len(mine), "agree_with_majority": agree})
    return out


@router.get("/report")
def monthly_report(month: str = None, db: Session = Depends(get_db), _: models.User = OFFICER):
    """Monthly compliance pack (CSV), one row per generator. month=YYYY-MM, default current."""
    import csv, io
    month = month or datetime.utcnow().strftime("%Y-%m")
    try:
        start = datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(400, "month must be YYYY-MM")
    end = datetime(start.year + (start.month == 12), start.month % 12 + 1, 1)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["month", "generator", "type", "pickups_done", "pickups_missed", "verdict_sorted", "verdict_mixed",
                "verdict_unclear", "segregation_rate_pct", "warnings", "notices", "fine_recommendations",
                "confirmed", "contested", "withdrawn_or_dismissed"])
    for g in db.query(models.Generator).all():
        pk = (db.query(models.Pickup).join(models.Bin).filter(models.Bin.generator_id == g.id,
              models.Pickup.created_at >= start, models.Pickup.created_at < end).all())
        vd = [p.evidence.verdict.final_verdict for p in pk if p.evidence and p.evidence.verdict]
        ns = db.query(models.Notice).filter(models.Notice.generator_id == g.id,
              models.Notice.created_at >= start, models.Notice.created_at < end).all()
        s, m, u = vd.count("sorted"), vd.count("mixed"), vd.count("unclear")
        w.writerow([month, g.name, g.type, sum(p.status == "done" for p in pk), sum(p.status == "missed" for p in pk),
                    s, m, u, round(100 * s / (s + m)) if s + m else "",
                    sum(n.level == "warning" for n in ns), sum(n.level == "notice" for n in ns),
                    sum(n.level == "fine_recommendation" for n in ns),
                    sum(n.status in ("confirmed", "upheld") for n in ns), sum(n.status == "contested" for n in ns),
                    sum(n.status in ("withdrawn", "dismissed") for n in ns)])
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="compliance_{month}.csv"'})
