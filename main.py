import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.grades_payments import grades_router, payments_router, salary_router, attendance_router, stats_router
from app.models import user, school, finance  # noqa

Base.metadata.create_all(bind=engine)

# Avtomatik seed - foydalanuvchilar yo'q bo'lsa yaratadi
def auto_seed():
    from app.core.database import SessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            users = [
                User(login="admin", password=hash_password("admin123"), first_name="Bozorov", last_name="Admin", role=UserRole.admin),
                User(login="akbar.teacher", password=hash_password("akbar123"), first_name="Akbar", last_name="Axmadov", role=UserRole.teacher),
                User(login="sardor.teacher", password=hash_password("sardor123"), first_name="Sardor", last_name="Yusupov", role=UserRole.teacher),
                User(login="nargiza.teacher", password=hash_password("nargiza123"), first_name="Nargiza", last_name="Xolova", role=UserRole.teacher),
                User(login="sherzod01", password=hash_password("sherzod123"), first_name="Sherzod", last_name="Zoirov", role=UserRole.student),
                User(login="pokiza02", password=hash_password("pokiza123"), first_name="Pokiza", last_name="Eshboriyeva", role=UserRole.student),
                User(login="resepshn", password=hash_password("resepshn123"), first_name="Malika", last_name="Holiqova", role=UserRole.receptionist),
            ]
            for u in users:
                db.add(u)
            db.commit()
            print("✅ Foydalanuvchilar yaratildi!")
    except Exception as e:
        print(f"Seed xato: {e}")
    finally:
        db.close()

auto_seed()

app = FastAPI(
    title="Bozorov School API",
    description="O'quv markaz boshqaruv tizimi",
    version="1.0.0"
)

# CORS - frontend URL larini qo'shing
origins = [
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "https://*.vercel.app",  # Vercel
    "*"  # Hozircha hammaga ruxsat
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(grades_router)
app.include_router(payments_router)
app.include_router(salary_router)
app.include_router(attendance_router)
app.include_router(stats_router)

@app.get("/")
def root():
    return {"message": "Bozorov School API ishlayapti! 🎓", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
