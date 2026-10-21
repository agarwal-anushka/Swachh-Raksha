from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, UniqueConstraint
)
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(150), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False)  # collector, reviewer, officer, admin
    zone = Column(String(50), nullable=True)
    generator_id = Column(Integer, ForeignKey("generators.id"), nullable=True)  # for role=generator
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pickups = relationship("Pickup", back_populates="collector")
    reviews = relationship("Review", back_populates="reviewer")


class Generator(Base):
    __tablename__ = "generators"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    type = Column(String(50))  # hostel, mess, academic, etc.
    address = Column(Text)
    contact_name = Column(String(100))
    contact_phone = Column(String(20))
    latitude = Column(Numeric(10, 7))   # registered site location (for the "near site" check)
    longitude = Column(Numeric(10, 7))
    zone = Column(String(50))  # reviewers from the same zone never see this generator's photos
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    bins = relationship("Bin", back_populates="generator")
    notices = relationship("Notice", back_populates="generator")


class Bin(Base):
    __tablename__ = "bins"

    id = Column(Integer, primary_key=True, index=True)
    generator_id = Column(Integer, ForeignKey("generators.id"), nullable=False)
    stream = Column(String(30), nullable=False)  # wet, dry, sanitary, special
    qr_code = Column(String(100), unique=True, nullable=False, index=True)
    label = Column(String(100))
    status = Column(String(20), default="active")
    created_at = Column(DateTime, default=datetime.utcnow)

    generator = relationship("Generator", back_populates="bins")
    pickups = relationship("Pickup", back_populates="bin")


class Pickup(Base):
    __tablename__ = "pickups"

    id = Column(Integer, primary_key=True, index=True)
    bin_id = Column(Integer, ForeignKey("bins.id"), nullable=False)
    collector_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    scheduled_date = Column(Date)
    status = Column(String(20), nullable=False)  # done, missed
    missed_reason = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    bin = relationship("Bin", back_populates="pickups")
    collector = relationship("User", back_populates="pickups")
    evidence = relationship("Evidence", back_populates="pickup", uselist=False)


class Evidence(Base):
    __tablename__ = "evidence"

    id = Column(Integer, primary_key=True, index=True)
    pickup_id = Column(Integer, ForeignKey("pickups.id"), nullable=False)
    photo_path = Column(String(500), nullable=False)
    photo_hash = Column(String(64), nullable=False)
    prev_hash = Column(String(64), unique=True)  # unique: DB itself refuses a forked chain
    this_hash = Column(String(64), nullable=False)
    device_time = Column(DateTime)
    server_time = Column(DateTime, nullable=False)
    latitude = Column(Numeric(10, 7))
    longitude = Column(Numeric(10, 7))
    created_at = Column(DateTime, default=datetime.utcnow)

    pickup = relationship("Pickup", back_populates="evidence")
    reviews = relationship("Review", back_populates="evidence")
    verdict = relationship("Verdict", back_populates="evidence", uselist=False)


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (UniqueConstraint("evidence_id", "reviewer_id", name="uq_evidence_reviewer"),)

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verdict = Column(String(20), nullable=False)  # sorted, mixed, unclear
    reviewed_at = Column(DateTime, default=datetime.utcnow)

    evidence = relationship("Evidence", back_populates="reviews")
    reviewer = relationship("User", back_populates="reviews")


class Verdict(Base):
    __tablename__ = "verdicts"

    id = Column(Integer, primary_key=True, index=True)
    evidence_id = Column(Integer, ForeignKey("evidence.id"), unique=True, nullable=False)
    final_verdict = Column(String(20), nullable=False)  # sorted, mixed, unclear
    sorted_count = Column(Integer, default=0)
    mixed_count = Column(Integer, default=0)
    unclear_count = Column(Integer, default=0)
    locked_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    evidence = relationship("Evidence", back_populates="verdict")


class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)
    generator_id = Column(Integer, ForeignKey("generators.id"), nullable=False)
    evidence_id = Column(Integer, ForeignKey("evidence.id"))
    level = Column(String(30), nullable=False)  # warning, notice, fine_recommendation
    status = Column(String(30), default="proposed")  # proposed, confirmed, dismissed, contested, upheld, withdrawn
    officer_id = Column(Integer, ForeignKey("users.id"))
    officer_remark = Column(Text)
    contest_text = Column(Text)
    issued_at = Column(DateTime)  # when the officer confirmed it and it became visible to the generator
    contested_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime)

    evidence = relationship("Evidence")
    generator = relationship("Generator", back_populates="notices")


class TestPhoto(Base):
    """Admin-supplied photo with a known answer, mixed invisibly into reviewers' queues."""
    __tablename__ = "test_photos"

    id = Column(Integer, primary_key=True, index=True)
    photo_path = Column(String(500), nullable=False)
    expected = Column(String(20), nullable=False)  # sorted | mixed
    created_at = Column(DateTime, default=datetime.utcnow)


class TestResponse(Base):
    __tablename__ = "test_responses"
    __table_args__ = (UniqueConstraint("test_id", "reviewer_id", name="uq_test_reviewer"),)

    id = Column(Integer, primary_key=True, index=True)
    test_id = Column(Integer, ForeignKey("test_photos.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    verdict = Column(String(20), nullable=False)
    correct = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
