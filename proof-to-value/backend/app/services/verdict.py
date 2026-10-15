from datetime import datetime
from sqlalchemy.orm import Session
from .. import models


def try_lock_verdict(db: Session, evidence_id: int) -> models.Verdict | None:
    """If 3 reviews exist, compute majority and lock. Returns Verdict or None."""
    reviews = (
        db.query(models.Review)
        .filter(models.Review.evidence_id == evidence_id)
        .all()
    )
    if len(reviews) < 3:
        return None

    # Already locked?
    existing = db.query(models.Verdict).filter(models.Verdict.evidence_id == evidence_id).first()
    if existing:
        return existing

    counts = {"sorted": 0, "mixed": 0, "unclear": 0}
    for r in reviews:
        if r.verdict in counts:
            counts[r.verdict] += 1

    # Majority
    final = max(counts, key=counts.get)
    # Tie-break: if no clear majority (all different), mark unclear
    if list(counts.values()).count(max(counts.values())) > 1:
        final = "unclear"

    verdict = models.Verdict(
        evidence_id=evidence_id,
        final_verdict=final,
        sorted_count=counts["sorted"],
        mixed_count=counts["mixed"],
        unclear_count=counts["unclear"],
        locked_at=datetime.utcnow(),
    )
    db.add(verdict)
    db.commit()
    db.refresh(verdict)

    # Auto-propose notice if mixed
    if final == "mixed":
        _propose_notice(db, evidence_id)

    return verdict


def _propose_notice(db: Session, evidence_id: int):
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        return
    pickup = evidence.pickup
    generator_id = pickup.bin.generator_id

    # Simple ladder: count previous mixed verdicts for this generator
    mixed_count = (
        db.query(models.Verdict)
        .join(models.Evidence)
        .join(models.Pickup)
        .join(models.Bin)
        .filter(
            models.Bin.generator_id == generator_id,
            models.Verdict.final_verdict == "mixed",
        )
        .count()
    )

    if mixed_count <= 1:
        level = "warning"
    elif mixed_count == 2:
        level = "notice"
    else:
        level = "fine_recommendation"

    notice = models.Notice(
        generator_id=generator_id,
        evidence_id=evidence_id,
        level=level,
        status="proposed",
    )
    db.add(notice)
    db.commit()
