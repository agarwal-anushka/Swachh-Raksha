from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal


# ---------- Auth ----------
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ---------- Users ----------
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: str
    zone: Optional[str] = None
    generator_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    zone: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


# ---------- Generators ----------
class GeneratorCreate(BaseModel):
    name: str
    type: Optional[str] = None
    address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    zone: Optional[str] = None


class GeneratorOut(BaseModel):
    id: int
    name: str
    type: Optional[str]
    address: Optional[str]
    contact_name: Optional[str]
    contact_phone: Optional[str]
    zone: Optional[str] = None
    status: str

    class Config:
        from_attributes = True


# ---------- Bins ----------
class BinCreate(BaseModel):
    generator_id: int
    stream: str
    label: Optional[str] = None


class BinOut(BaseModel):
    id: int
    generator_id: int
    stream: str
    qr_code: str
    label: Optional[str]
    status: str
    generator_name: Optional[str] = None

    class Config:
        from_attributes = True


# ---------- Pickup + Evidence ----------
class PickupCreate(BaseModel):
    bin_qr: str
    status: str  # done | missed
    missed_reason: Optional[str] = None
    device_time: Optional[datetime] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None


class EvidenceOut(BaseModel):
    id: int
    photo_path: str
    photo_hash: str
    this_hash: str
    prev_hash: Optional[str]
    server_time: datetime
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]

    class Config:
        from_attributes = True


class PickupOut(BaseModel):
    id: int
    bin_id: int
    collector_id: int
    status: str
    created_at: datetime
    evidence: Optional[EvidenceOut] = None

    class Config:
        from_attributes = True


# ---------- Reviews ----------
class ReviewCreate(BaseModel):
    evidence_id: int
    verdict: str  # sorted | mixed | unclear


class ReviewOut(BaseModel):
    id: int
    evidence_id: int
    reviewer_id: int
    verdict: str
    reviewed_at: datetime

    class Config:
        from_attributes = True


class VerdictOut(BaseModel):
    id: int
    evidence_id: int
    final_verdict: str
    sorted_count: int
    mixed_count: int
    unclear_count: int
    locked_at: datetime

    class Config:
        from_attributes = True


# ---------- Notices ----------
class NoticeAction(BaseModel):
    action: str  # confirm | dismiss | uphold | withdraw
    remark: Optional[str] = None


class ContestIn(BaseModel):
    text: str


# ---------- Reviewer queue item (deliberately minimal: blind review) ----------
class ReviewQueueItem(BaseModel):
    evidence_id: int
    photo_url: str
    created_at: datetime
