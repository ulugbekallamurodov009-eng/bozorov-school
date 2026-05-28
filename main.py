import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.grades_payments import grades_router, payments_router
from app.models import user, school, finance  # noqa

Base.metadata.create_all(bind=engine)

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

@app.get("/")
def root():
    return {"message": "Bozorov School API ishlayapti! 🎓", "version": "1.0.0"}

@app.get("/health")
def health():
    return {"status": "ok"}
