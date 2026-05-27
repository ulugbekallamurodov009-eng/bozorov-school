from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, get_current_user
from app.models.user import User
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["Auth"])

class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    full_name: str
    user_id: int

class MeResponse(BaseModel):
    id: int
    login: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True

@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Foydalanuvchini topish
    user = db.query(User).filter(User.login == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Login yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Hisobingiz bloklangan. Administratorga murojaat qiling."
        )

    # Token yaratish
    token = create_access_token(data={"sub": str(user.id), "role": user.role})

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        role=user.role,
        full_name=user.full_name,
        user_id=user.id
    )

@router.get("/me", response_model=MeResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return MeResponse(
        id=current_user.id,
        login=current_user.login,
        full_name=current_user.full_name,
        role=current_user.role,
        is_active=current_user.is_active
    )

@router.post("/logout")
def logout():
    # Frontend tokenni o'chiradi
    return {"message": "Muvaffaqiyatli chiqildi"}
