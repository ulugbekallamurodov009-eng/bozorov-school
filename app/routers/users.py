from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import hash_password, get_current_user
from app.models.user import User, UserRole
from app.models.school import Student, Teacher
import random, string

router = APIRouter(prefix="/api/users", tags=["Users"])

# ---- SCHEMAS ----
class CreateUserRequest(BaseModel):
    first_name:    str
    last_name:     str
    phone:         Optional[str] = None
    role:          UserRole
    # Custom login/password (ixtiyoriy)
    custom_login:  Optional[str] = None
    custom_pass:   Optional[str] = None
    # O'qituvchi uchun
    subject:       Optional[str] = None
    salary_pct:    Optional[float] = 30.0
    salary_type:   Optional[str] = "pct"
    # O'quvchi uchun
    group_id:      Optional[int] = None

class UserResponse(BaseModel):
    id:         int
    login:      str
    password_plain: str  # Faqat yaratilganda ko'rsatiladi
    full_name:  str
    role:       str
    phone:      Optional[str]

class UserListItem(BaseModel):
    id:        int
    login:     str
    full_name: str
    role:      str
    phone:     Optional[str]
    is_active: bool

    class Config:
        from_attributes = True

# ---- HELPERS ----
def generate_login(first: str, last: str, role: str) -> str:
    f = first.lower().replace(" ", "")[:6]
    l = last.lower().replace(" ", "")[:3]
    if role == "teacher":
        return f"{f}.teacher"
    num = random.randint(10, 99)
    return f"{f}{num}"

def generate_password(length=8) -> str:
    chars = string.ascii_letters + string.digits + "@#!"
    return "".join(random.choices(chars, k=length))

def make_login_unique(base_login: str, db: Session) -> str:
    login = base_login
    counter = 1
    while db.query(User).filter(User.login == login).first():
        login = f"{base_login}{counter}"
        counter += 1
    return login

# ---- ENDPOINTS ----
@router.post("/create", response_model=UserResponse)
def create_user(
    data: CreateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Faqat admin yarata oladi
    if current_user.role not in [UserRole.admin, UserRole.receptionist]:
        raise HTTPException(status_code=403, detail="Ruxsat yoq")

    # Receptionist faqat student yarata oladi
    if current_user.role == UserRole.receptionist and data.role != UserRole.student:
        raise HTTPException(status_code=403, detail="Resepshn faqat oquvchi yarata oladi")
    # Admin barcha rollarni yarata oladi

    # Login va parol - custom yoki avtomatik
    if data.custom_login and data.custom_login.strip():
        login = data.custom_login.strip()
        # Check uniqueness
        if db.query(User).filter(User.login == login).first():
            raise HTTPException(status_code=400, detail=f"Login '{login}' band! Boshqa login tanlang.")
    else:
        base_login = generate_login(data.first_name, data.last_name, data.role)
        login = make_login_unique(base_login, db)
    
    plain_password = data.custom_pass.strip() if data.custom_pass and data.custom_pass.strip() else generate_password()

    # User yaratish
    user = User(
        login=login,
        password=hash_password(plain_password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role=data.role
    )
    db.add(user)
    db.flush()

    # Rol profili yaratish
    if data.role == UserRole.teacher:
        teacher = Teacher(
            user_id=user.id,
            subject=data.subject or "Noma'lum",
            salary_pct=data.salary_pct or 30.0,
            salary_type=data.salary_type or "pct"
        )
        db.add(teacher)

    elif data.role == UserRole.student:
        student = Student(user_id=user.id)
        db.add(student)
        db.flush()

        # Guruhga qo'shish
        if data.group_id:
            from app.models.school import Group
            group = db.query(Group).filter(Group.id == data.group_id).first()
            if group:
                group.students.append(student)

    db.commit()

    return UserResponse(
        id=user.id,
        login=login,
        password_plain=plain_password,
        full_name=user.full_name,
        role=user.role,
        phone=user.phone
    )

@router.get("/list", response_model=List[UserListItem])
def list_users(
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.all()

@router.put("/{user_id}/toggle-active")
def toggle_user_active(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")

    user.is_active = not user.is_active
    db.commit()
    return {"message": f"Holat: {'aktiv' if user.is_active else 'bloklangan'}"}

@router.put("/{user_id}/reset-password")
def reset_password(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Topilmadi")

    new_pass = generate_password()
    user.password = hash_password(new_pass)
    db.commit()
    return {"message": "Parol yangilandi", "new_password": new_pass}
