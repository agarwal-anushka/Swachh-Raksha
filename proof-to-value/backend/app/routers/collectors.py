import os
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, auth
from ..services.hash_chain import compute_photo_hash, compute_this_hash, get_latest_hash, CHAIN_LOCK
from ..services.photos import validate_image

router = APIRouter(prefix="/collector", tags=["collector"])


@router.get("/stats")
def my_stats(db: Session = Depends(get_db), current_user: models.User = Depends(auth.require_role("collector", "admin"))):
    from .officers import collector_stats
    return collector_stats(db, current_user.id)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def _naive_utc(iso: str | None):
    """Parse the phone's clock and store it as naive UTC so hashes are stable."""
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return d.astimezone(timezone.utc).replace(tzinfo=None) if d.tzinfo else d


@router.get("/bin/{qr_code}", response_model=schemas.BinOut)
def get_bin_by_qr(
    qr_code: str,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("collector", "admin")),
):
    bin_obj = db.query(models.Bin).filter(models.Bin.qr_code == qr_code).first()
    if not bin_obj:
        raise HTTPException(404, "Bin not found")
    out = schemas.BinOut.model_validate(bin_obj)
    out.generator_name = bin_obj.generator.name if bin_obj.generator else None
    return out


@router.post("/pickup", response_model=schemas.PickupOut)
async def submit_pickup(
    bin_qr: str = Form(...),
    status: str = Form(...),
    missed_reason: str = Form(None),
    device_time: str = Form(None),
    latitude: float = Form(None),
    longitude: float = Form(None),
    photo: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.require_role("collector", "admin")),
):
    bin_obj = db.query(models.Bin).filter(models.Bin.qr_code == bin_qr).first()
    if not bin_obj:
        raise HTTPException(404, "Bin not found")
    if status not in ("done", "missed"):
        raise HTTPException(400, "status must be 'done' or 'missed'")

    content = b""
    if status == "done":
        # A completed pickup without evidence is not allowed.
        if photo is None:
            raise HTTPException(400, "A photo is required for a completed pickup")
        content = await photo.read()
        if not content:
            raise HTTPException(400, "Empty photo")
        try:
            validate_image(content)
        except Exception:
            raise HTTPException(400, "File is not a valid image")

    if status == "done" and db.query(models.Evidence).filter(
            models.Evidence.photo_hash == compute_photo_hash(content)).first():
        raise HTTPException(409, "This exact photo was already submitted. Take a fresh photo at the bin.")

    with CHAIN_LOCK:  # one writer extends the chain at a time
        pickup = models.Pickup(
            bin_id=bin_obj.id,
            collector_id=current_user.id,
            scheduled_date=datetime.utcnow().date(),
            status=status,
            missed_reason=missed_reason if status == "missed" else None,
        )
        db.add(pickup)
        db.flush()  # get pickup.id without committing yet

        if status == "done":
            photo_hash = compute_photo_hash(content)
            server_time = datetime.utcnow()
            dev_time = _naive_utc(device_time)
            prev_hash = get_latest_hash(db)
            this_hash = compute_this_hash(photo_hash, pickup.id, bin_obj.id, server_time,
                                          dev_time, latitude, longitude, prev_hash)
            filename = f"{this_hash[:16]}_{pickup.id}.jpg"
            with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
                f.write(content)
            db.add(models.Evidence(
                pickup_id=pickup.id, photo_path=filename, photo_hash=photo_hash,
                prev_hash=prev_hash, this_hash=this_hash, device_time=dev_time,
                server_time=server_time, latitude=latitude, longitude=longitude,
            ))
        db.commit()
    db.refresh(pickup)
    return pickup
