from datetime import datetime, timedelta
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

    # Majority (2 of 3). A 1-1-1 split has no majority -> "unclear".
    # "unclear" never creates a notice: only a clear majority of "mixed" does.
    final = max(counts, key=counts.get)
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


def mixed_in_window(db: Session, generator_id: int, days: int = 30) -> int:
    """Locked 'mixed' verdicts for this generator in the last `days` days."""
    since = datetime.utcnow() - timedelta(days=days)
    return (
        db.query(models.Verdict)
        .join(models.Evidence, models.Verdict.evidence_id == models.Evidence.id)
        .join(models.Pickup, models.Evidence.pickup_id == models.Pickup.id)
        .join(models.Bin, models.Pickup.bin_id == models.Bin.id)
        .filter(
            models.Bin.generator_id == generator_id,
            models.Verdict.final_verdict == "mixed",
            models.Verdict.locked_at >= since,
        )
        .count()
    )


def _propose_notice(db: Session, evidence_id: int):
    """One notice per locked 'mixed' verdict. Ladder is per generator, 30-day window."""
    if db.query(models.Notice).filter(models.Notice.evidence_id == evidence_id).first():
        return
    evidence = db.query(models.Evidence).filter(models.Evidence.id == evidence_id).first()
    if not evidence:
        return
    generator_id = evidence.pickup.bin.generator_id
    n = mixed_in_window(db, generator_id)  # includes this verdict (already committed)

    level = "warning" if n <= 1 else "notice" if n == 2 else "fine_recommendation"
    db.add(models.Notice(generator_id=generator_id, evidence_id=evidence_id,
                         level=level, status="proposed"))
    db.commit()
