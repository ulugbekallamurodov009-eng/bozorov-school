from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, UserRole
from app.models.school import Student, Group
from app.models.finance import Grade, GradeType, Payment, PaymentStatus

grades_router   = APIRouter(prefix="/api/grades",   tags=["Grades"])
payments_router = APIRouter(prefix="/api/payments", tags=["Payments"])

# ======== GRADES ========
class GradeCreate(BaseModel):
    student_id: int
    group_id:   int
    score:      float
    max_score:  float = 30.0
    topic:      Optional[str] = None
    grade_type: GradeType = GradeType.daily
    note:       Optional[str] = None

class GradeResponse(BaseModel):
    id:         int
    student_id: int
    score:      float
    max_score:  float
    percentage: float
    topic:      Optional[str]
    grade_type: str
    date:       datetime

    class Config:
        from_attributes = True

@grades_router.post("/add", response_model=GradeResponse)
def add_grade(
    data: GradeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role not in [UserRole.teacher, UserRole.admin]:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    teacher_id = 1  # Demo
    if current_user.role == UserRole.teacher and current_user.teacher_profile:
        teacher_id = current_user.teacher_profile.id

    grade = Grade(
        student_id=data.student_id,
        teacher_id=teacher_id,
        group_id=data.group_id,
        score=data.score,
        max_score=data.max_score,
        topic=data.topic,
        grade_type=data.grade_type,
        note=data.note
    )
    db.add(grade)
    db.commit()
    db.refresh(grade)
    return grade

@grades_router.get("/student/{student_id}", response_model=List[GradeResponse])
def get_student_grades(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    grades = db.query(Grade).filter(Grade.student_id == student_id).all()
    return grades

@grades_router.get("/group/{group_id}")
def get_group_grades(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    grades = db.query(Grade).filter(Grade.group_id == group_id).all()
    result = []
    for g in grades:
        result.append({
            "id": g.id,
            "student_id": g.student_id,
            "score": g.score,
            "max_score": g.max_score,
            "percentage": g.percentage,
            "topic": g.topic,
            "grade_type": g.grade_type,
            "date": g.date
        })
    return result

# ======== PAYMENTS ========
class PaymentCreate(BaseModel):
    student_id: int
    group_id:   int
    amount:     float
    month:      str   # "2026-06"
    method:     Optional[str] = "cash"
    note:       Optional[str] = None

class PaymentUpdate(BaseModel):
    paid_amount: float
    method:      Optional[str] = None
    note:        Optional[str] = None

class PaymentResponse(BaseModel):
    id:          int
    student_id:  int
    amount:      float
    paid_amount: float
    remaining:   float
    month:       str
    status:      str
    method:      Optional[str]
    paid_at:     Optional[datetime]

    class Config:
        from_attributes = True

@payments_router.post("/create", response_model=PaymentResponse)
def create_payment(
    data: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    # Bir xil oy uchun ikki marta yaratmaslik
    existing = db.query(Payment).filter(
        Payment.student_id == data.student_id,
        Payment.month == data.month
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Bu oy uchun to'lov allaqachon mavjud")

    payment = Payment(
        student_id=data.student_id,
        group_id=data.group_id,
        amount=data.amount,
        month=data.month,
        method=data.method,
        note=data.note
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment

@payments_router.put("/{payment_id}/pay", response_model=PaymentResponse)
def pay(
    payment_id: int,
    data: PaymentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Topilmadi")

    p.paid_amount = data.paid_amount
    p.method = data.method or p.method
    p.note = data.note or p.note

    if p.paid_amount >= p.amount:
        p.status = PaymentStatus.paid
        p.paid_at = datetime.utcnow()
    elif p.paid_amount > 0:
        p.status = PaymentStatus.partial
    else:
        p.status = PaymentStatus.unpaid

    db.commit()
    db.refresh(p)
    return p

@payments_router.get("/student/{student_id}")
def student_payments(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    payments = db.query(Payment).filter(Payment.student_id == student_id).all()
    return [{"id":p.id,"amount":p.amount,"paid_amount":p.paid_amount,
             "remaining":p.remaining,"month":p.month,"status":p.status,
             "method":p.method,"paid_at":p.paid_at} for p in payments]

@payments_router.get("/summary/{month}")
def monthly_summary(
    month: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")

    payments = db.query(Payment).filter(Payment.month == month).all()
    total  = sum(p.amount for p in payments)
    paid   = sum(p.paid_amount for p in payments)
    unpaid = len([p for p in payments if p.status == PaymentStatus.unpaid])
    partial= len([p for p in payments if p.status == PaymentStatus.partial])
    done   = len([p for p in payments if p.status == PaymentStatus.paid])

    return {
        "month": month,
        "total_expected": total,
        "total_collected": paid,
        "paid_count": done,
        "unpaid_count": unpaid,
        "partial_count": partial
    }
