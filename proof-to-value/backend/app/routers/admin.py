import io, os, uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import List
from ..database import get_db
from .. import models, schemas, auth

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", response_model=schemas.UserOut)
def create_user(
    payload: schemas.UserCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("admin")),
):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(400, "Email already registered")
    user = models.User(
        name=payload.name,
        email=payload.email,
        password_hash=auth.get_password_hash(payload.password),
        role=payload.role,
        zone=payload.zone,
        generator_id=payload.generator_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=List[schemas.UserOut])
def list_users(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("admin")),
):
    return db.query(models.User).all()


@router.post("/generators", response_model=schemas.GeneratorOut)
def create_generator(
    payload: schemas.GeneratorCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("admin")),
):
    gen = models.Generator(**payload.model_dump())
    db.add(gen)
    db.commit()
    db.refresh(gen)
    return gen


@router.get("/generators", response_model=List[schemas.GeneratorOut])
def list_generators(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("admin", "officer")),
):
    return db.query(models.Generator).all()


@router.post("/bins", response_model=schemas.BinOut)
def create_bin(
    payload: schemas.BinCreate,
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("admin")),
):
    gen = db.query(models.Generator).filter(models.Generator.id == payload.generator_id).first()
    if not gen:
        raise HTTPException(404, "Generator not found")

    # Generate QR code: PTV-2026-XXXXX
    count = db.query(models.Bin).count() + 1
    qr = f"PTV-2026-{count:05d}"

    bin_obj = models.Bin(
        generator_id=payload.generator_id,
        stream=payload.stream.lower(),
        qr_code=qr,
        label=payload.label or f"{gen.name} - {payload.stream}",
    )
    db.add(bin_obj)
    db.commit()
    db.refresh(bin_obj)

    out = schemas.BinOut.model_validate(bin_obj)
    out.generator_name = gen.name
    return out


@router.get("/bins", response_model=List[schemas.BinOut])
def list_bins(
    db: Session = Depends(get_db),
    _: models.User = Depends(auth.require_role("admin", "officer", "collector")),
):
    bins = db.query(models.Bin).all()
    result = []
    for b in bins:
        item = schemas.BinOut.model_validate(b)
        item.generator_name = b.generator.name if b.generator else None
        result.append(item)
    return result


UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
ADMIN = Depends(auth.require_role("admin"))


@router.get("/bins/{bin_id}/qr.png")
def bin_qr(bin_id: int, db: Session = Depends(get_db), _: models.User = ADMIN):
    import qrcode
    b = db.query(models.Bin).filter(models.Bin.id == bin_id).first()
    if not b:
        raise HTTPException(404, "Bin not found")
    buf = io.BytesIO()
    qrcode.make(b.qr_code).save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


@router.post("/test-photos")
async def add_test_photo(expected: str = Form(...), photo: UploadFile = File(...),
                         db: Session = Depends(get_db), _: models.User = ADMIN):
    """Known-answer photo that is silently mixed into reviewers' queues."""
    from ..services.photos import validate_image
    if expected not in ("sorted", "mixed"):
        raise HTTPException(400, "expected must be sorted or mixed")
    content = await photo.read()
    try:
        validate_image(content)
    except Exception:
        raise HTTPException(400, "File is not a valid image")
    name = f"test_{uuid.uuid4().hex[:12]}.jpg"
    with open(os.path.join(UPLOAD_DIR, name), "wb") as f:
        f.write(content)
    t = models.TestPhoto(photo_path=name, expected=expected)
    db.add(t)
    db.commit()
    return {"id": t.id, "expected": expected}


@router.get("/test-photos")
def list_test_photos(db: Session = Depends(get_db), _: models.User = ADMIN):
    return [{"id": t.id, "expected": t.expected} for t in db.query(models.TestPhoto).all()]


@router.patch("/generators/{generator_id}/location")
def set_location(generator_id: int, payload: schemas.LocationIn, db: Session = Depends(get_db), _: models.User = ADMIN):
    """Register where a generator's bins are. Photos are compared against this point."""
    g = db.query(models.Generator).filter(models.Generator.id == generator_id).first()
    if not g:
        raise HTTPException(404, "Generator not found")
    if not (-90 <= payload.latitude <= 90 and -180 <= payload.longitude <= 180):
        raise HTTPException(400, "Invalid coordinates")
    g.latitude, g.longitude = payload.latitude, payload.longitude
    db.commit()
    return {"id": g.id, "latitude": payload.latitude, "longitude": payload.longitude}
