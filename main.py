from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import engine, Base
from app.routers.auth import router as auth_router
from app.routers.users import router as users_router
from app.routers.grades_payments import grades_router, payments_router

# Barcha modellarni import qilish (jadval yaratish uchun)
from app.models import user, school, finance  # noqa

# Ma'lumotlar bazasi jadvallarini yaratish
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Bozorov School API",
    description="O'quv markaz boshqaruv tizimi",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - Frontend bilan ishlash uchun
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production da aniq domenlarni yozing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routerlarni ulash
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(grades_router)
app.include_router(payments_router)

@app.get("/")
def root():
    return {
        "message": "Bozorov School API ishlayapti! 🎓",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
