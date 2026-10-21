import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base, SessionLocal
from . import models, auth
from .routers import auth as auth_router
from .routers import admin as admin_router
from .routers import collectors as collectors_router
from .routers import reviews as reviews_router
from .routers import officers as officers_router
from .routers import generator as generator_router

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

# Photos are NOT served as static files: every photo goes through an
# authenticated, role-checked endpoint (reviewer copy / officer / generator).
os.makedirs(os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"), exist_ok=True)

# Routers
app.include_router(auth_router.router)
app.include_router(admin_router.router)
app.include_router(collectors_router.router)
app.include_router(reviews_router.router)
app.include_router(officers_router.router)
app.include_router(generator_router.router)


@app.get("/")
def root():
    return {"message": "Proof-to-Value API is running", "docs": "/docs"}


@app.on_event("startup")
def seed_data():
    """Create default admin + sample data if empty."""
    db = SessionLocal()
    try:
        if db.query(models.User).count() == 0:
            gens = [
                models.Generator(name="Hostel Block A", type="hostel", address="North Campus", contact_name="Warden A", contact_phone="9000000001", zone="Zone-1"),
                models.Generator(name="Central Mess", type="mess", address="Main Campus", contact_name="Mess Manager", contact_phone="9000000002", zone="Zone-2"),
                models.Generator(name="Academic Block C", type="academic", address="South Campus", contact_name="Admin C", contact_phone="9000000003", zone="Zone-3"),
            ]
            db.add_all(gens)
            db.commit()

            H = auth.get_password_hash
            users = [
                models.User(name="Admin", email="admin@ptv.local", password_hash=H("admin123"), role="admin"),
                models.User(name="Collector One", email="collector@ptv.local", password_hash=H("collect123"), role="collector", zone="Campus-A"),
                models.User(name="Reviewer A", email="reviewer1@ptv.local", password_hash=H("review123"), role="reviewer", zone="Zone-1"),
                models.User(name="Reviewer B", email="reviewer2@ptv.local", password_hash=H("review123"), role="reviewer", zone="Zone-2"),
                models.User(name="Reviewer C", email="reviewer3@ptv.local", password_hash=H("review123"), role="reviewer", zone="Zone-3"),
                models.User(name="Reviewer D", email="reviewer4@ptv.local", password_hash=H("review123"), role="reviewer", zone="Zone-4"),
                models.User(name="Case Officer", email="officer@ptv.local", password_hash=H("officer123"), role="officer"),
                models.User(name="Hostel A Warden", email="generator@ptv.local", password_hash=H("generator123"), role="generator", generator_id=gens[0].id),
            ]
            db.add_all(users)
            db.commit()

            bins = [
                models.Bin(generator_id=1, stream="wet", qr_code="PTV-2026-00001", label="Hostel A - Wet"),
                models.Bin(generator_id=1, stream="dry", qr_code="PTV-2026-00002", label="Hostel A - Dry"),
                models.Bin(generator_id=2, stream="wet", qr_code="PTV-2026-00003", label="Mess - Wet"),
                models.Bin(generator_id=2, stream="dry", qr_code="PTV-2026-00004", label="Mess - Dry"),
                models.Bin(generator_id=3, stream="wet", qr_code="PTV-2026-00005", label="Academic C - Wet"),
            ]
            db.add_all(bins)
            db.commit()

            # FICTIONAL demo generators. Names are invented ("(Demo)"); localities are real areas of
            # Gwalior used only so the data looks local. None of these are real establishments.
            demo = [
                ("Hotel Shri Gwalior Palace (Demo)", "hotel", "Zone-1", "Near City Centre, Gwalior"),
                ("Maa Sharda Marriage Garden (Demo)", "banquet", "Zone-2", "Jhansi Road, Gwalior"),
                ("Jan Seva Hospital (Demo)", "hospital", "Zone-3", "Thatipur, Gwalior"),
                ("Fort View Mall (Demo)", "mall", "Zone-4", "Gola Ka Mandir, Gwalior"),
                ("Saraswati Vidya Mandir (Demo)", "school", "Zone-1", "Morar, Gwalior"),
                ("Lashkar Sabzi Mandi (Demo)", "market", "Zone-2", "Lashkar, Gwalior"),
                ("Rail Yatri Canteen (Demo)", "canteen", "Zone-3", "Near Railway Station, Gwalior"),
                ("Vigyan Engineering College (Demo)", "college", "Zone-4", "Bhind Road, Gwalior"),
                ("Shri Balaji Mithai Bhandar (Demo)", "restaurant", "Zone-1", "Hazira, Gwalior"),
                ("Radhe Krishna Vatika (Demo)", "banquet", "Zone-2", "Padav, Gwalior"),
                ("Zila Karyalaya Canteen (Demo)", "office", "Zone-3", "Maharaj Bada, Gwalior"),
                ("Phool Bagh Cinema Hall (Demo)", "mall", "Zone-4", "Phool Bagh, Gwalior"),
            ]
            n = len(bins)
            for name, typ, zone, addr in demo:
                g = models.Generator(name=name, type=typ, address=addr, zone=zone,
                                     contact_name="Demo contact", contact_phone="9000000000")
                db.add(g)
                db.flush()
                for stream in ("wet", "dry"):
                    n += 1
                    db.add(models.Bin(generator_id=g.id, stream=stream, qr_code=f"PTV-2026-{n:05d}",
                                      label=f"{name} - {stream.title()}"))
            db.commit()
            print("✅ Seed data created")
            print("   admin@ptv.local / admin123")
            print("   collector@ptv.local / collect123")
            print("   reviewer1-4@ptv.local / review123  (reviewers never see their own zone's generators)")
            print("   generator@ptv.local / generator123")
            print("   officer@ptv.local / officer123")
    finally:
        db.close()
