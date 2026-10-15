import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base, SessionLocal
from . import models, auth
from .routers import auth as auth_router
from .routers import admin as admin_router
from .routers import collectors as collectors_router
from .routers import reviews as reviews_router
from .routers import officers as officers_router

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Proof-to-Value API",
    description="Evidence-based waste segregation system for Gwalior BWGs – Pilot",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded photos
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# Routers
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(collectors_router.router)
app.include_router(reviews_router.router)
app.include_router(officers_router.router)


@app.get("/")
def root():
    return {"message": "Proof-to-Value API is running", "docs": "/docs"}


@app.on_event("startup")
def seed_data():
    """Create default admin + sample data if empty."""
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            users = [
                models.User(name="Admin", email="admin@ptv.local", password_hash=auth.get_password_hash("admin123"), role="admin"),
                models.User(name="Collector One", email="collector@ptv.local", password_hash=auth.get_password_hash("collect123"), role="collector", zone="Campus-A"),
                models.User(name="Reviewer A", email="reviewer1@ptv.local", password_hash=auth.get_password_hash("review123"), role="reviewer", zone="Zone-1"),
                models.User(name="Reviewer B", email="reviewer2@ptv.local", password_hash=auth.get_password_hash("review123"), role="reviewer", zone="Zone-2"),
                models.User(name="Reviewer C", email="reviewer3@ptv.local", password_hash=auth.get_password_hash("review123"), role="reviewer", zone="Zone-3"),
                models.User(name="Case Officer", email="officer@ptv.local", password_hash=auth.get_password_hash("officer123"), role="officer"),
            ]
            db.add_all(users)
            db.commit()

            # Sample generators
            gens = [
                models.Generator(name="Hostel Block A", type="hostel", address="North Campus", contact_name="Warden A", contact_phone="9000000001"),
                models.Generator(name="Central Mess", type="mess", address="Main Campus", contact_name="Mess Manager", contact_phone="9000000002"),
                models.Generator(name="Academic Block C", type="academic", address="South Campus", contact_name="Admin C", contact_phone="9000000003"),
            ]
            db.add_all(gens)
            db.commit()

            # Sample bins
            bins = [
                models.Bin(generator_id=1, stream="wet", qr_code="PTV-2026-00001", label="Hostel A - Wet"),
                models.Bin(generator_id=1, stream="dry", qr_code="PTV-2026-00002", label="Hostel A - Dry"),
                models.Bin(generator_id=2, stream="wet", qr_code="PTV-2026-00003", label="Mess - Wet"),
                models.Bin(generator_id=2, stream="dry", qr_code="PTV-2026-00004", label="Mess - Dry"),
                models.Bin(generator_id=3, stream="wet", qr_code="PTV-2026-00005", label="Academic C - Wet"),
            ]
            db.add_all(bins)
            db.commit()
            print("✅ Seed data created")
            print("   admin@ptv.local / admin123")
            print("   collector@ptv.local / collect123")
            print("   reviewer1/2/3@ptv.local / review123")
            print("   officer@ptv.local / officer123")
    finally:
        db.close()
