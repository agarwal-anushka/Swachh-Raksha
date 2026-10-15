from fastapi import APIRouter, Depends, HTTPException
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
