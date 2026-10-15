import os
import aiofiles
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from ..database import get_db
from .. import models, schemas, auth
from ..services.hash_chain import compute_photo_hash, compute_this_hash, get_latest_hash

router = APIRouter(prefix="/collector", tags=["collector"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


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

    pickup = models.Pickup(
        bin_id=bin_obj.id,
        collector_id=current_user.id,
        scheduled_date=datetime.utcnow().date(),
        status=status,
        missed_reason=missed_reason if status == "missed" else None,
    )
    db.add(pickup)
    db.commit()
    db.refresh(pickup)

    # If done + photo provided → create evidence
    if status == "done" and photo is not None:
        content = await photo.read()
        if len(content) == 0:
            raise HTTPException(400, "Empty photo")

        photo_hash = compute_photo_hash(content)
        server_time = datetime.utcnow()
        prev_hash = get_latest_hash(db)
        this_hash = compute_this_hash(photo_hash, server_time, prev_hash)

        # Save file
        filename = f"{this_hash[:16]}_{pickup.id}.jpg"
        filepath = os.path.join(UPLOAD_DIR, filename)
        async with aiofiles.open(filepath, "wb") as f:
            await f.write(content)

        evidence = models.Evidence(
            pickup_id=pickup.id,
            photo_path=filename,
            photo_hash=photo_hash,
            prev_hash=prev_hash,
            this_hash=this_hash,
            device_time=datetime.fromisoformat(device_time) if device_time else None,
            server_time=server_time,
            latitude=latitude,
            longitude=longitude,
        )
        db.add(evidence)
        db.commit()
        db.refresh(pickup)

    return pickup
