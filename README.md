# 🎓 Bozorov School — Backend API

## Texnologiyalar
- **Python 3.12** + **FastAPI**
- **SQLAlchemy** — ORM
- **SQLite** (development) → **PostgreSQL** (production)
- **JWT** — autentifikatsiya
- **Bcrypt** — parol xeshlash

## Loyiha strukturasi
```
bs/
├── main.py              # Asosiy kirish nuqtasi
├── seed.py              # Demo ma'lumotlar
├── bozorov_school.db    # SQLite bazasi
└── app/
    ├── core/
    │   ├── database.py  # DB konfiguratsiya
    │   └── security.py  # JWT, parol
    ├── models/
    │   ├── user.py      # Foydalanuvchi modeli
    │   ├── school.py    # O'qituvchi, O'quvchi, Guruh
    │   └── finance.py   # Baho, To'lov, Oylik
    └── routers/
        ├── auth.py               # Login, logout
        ├── users.py              # Login yaratish
        └── grades_payments.py    # Baholar, To'lovlar
```

## Ishga tushirish
```bash
# 1. O'rnatish
pip install fastapi uvicorn sqlalchemy python-jose passlib[bcrypt] python-multipart

# 2. Demo ma'lumotlar yuklash
python seed.py

# 3. Serverni ishga tushirish
uvicorn main:app --reload

# 4. API docs
# http://localhost:8000/docs
```

## Kirish ma'lumotlari (demo)
| Rol | Login | Parol |
|-----|-------|-------|
| Admin | admin | admin123 |
| O'qituvchi | akbar.teacher | akbar123 |
| O'quvchi | sherzod01 | sherzod123 |

## API endpointlar
| Method | URL | Tavsif |
|--------|-----|--------|
| POST | /api/auth/login | Kirish |
| GET | /api/auth/me | Joriy foydalanuvchi |
| POST | /api/users/create | Yangi login yaratish |
| GET | /api/users/list | Foydalanuvchilar |
| POST | /api/grades/add | Baho qo'yish |
| GET | /api/grades/student/{id} | O'quvchi baholari |
| POST | /api/payments/create | To'lov yaratish |
| PUT | /api/payments/{id}/pay | To'lov qabul qilish |
| GET | /api/payments/summary/{month} | Oylik hisobot |

## Keyingi qadamlar
- [ ] Groups router (guruhlar CRUD)
- [ ] Schedule router (jadval)
- [ ] Teacher salary router (oylik hisob)
- [ ] Statistics router (umumiy statistika)
- [ ] PostgreSQL ga o'tish
- [ ] Click/Payme integratsiya
- [ ] SMS (Eskiz) integratsiya
