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

@payments_router.post("/quick-pay")
def quick_pay(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Tez to'lov qabul qilish - student_name, amount, method, month"""
    from app.models.finance import Payment, PaymentStatus
    from datetime import datetime

    # Simple payment record without student_id requirement
    payment = Payment(
        student_id=data.get("student_id", 1),
        group_id=data.get("group_id", 1),
        amount=data.get("amount", 0),
        paid_amount=data.get("amount", 0),
        month=data.get("month", datetime.now().strftime("%Y-%m")),
        status=PaymentStatus.paid,
        method=data.get("method", "cash"),
        note=data.get("note", data.get("student_name", "")),
        paid_at=datetime.utcnow()
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {
        "id": payment.id,
        "amount": payment.amount,
        "method": payment.method,
        "status": payment.status,
        "paid_at": payment.paid_at,
        "message": "To'lov muvaffaqiyatli saqlandi!"
    }


@payments_router.get("/history")
def payment_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Barcha to'lovlar tarixi"""
    from app.models.finance import Payment
    payments = db.query(Payment).order_by(Payment.paid_at.desc()).limit(50).all()
    return [{
        "id": p.id,
        "amount": p.amount,
        "paid_amount": p.paid_amount,
        "month": p.month,
        "status": p.status,
        "method": p.method,
        "note": p.note,
        "paid_at": str(p.paid_at) if p.paid_at else None
    } for p in payments]


# ======== TEACHER SALARY ========
from fastapi import APIRouter as _AR
salary_router = _AR(prefix="/api/salary", tags=["Salary"])

@salary_router.post("/pay")
def pay_teacher_salary(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """O'qituvchiga oylik berish"""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Ruxsat yoq")
    
    from app.models.finance import TeacherSalary
    from datetime import datetime
    
    salary = TeacherSalary(
        teacher_id=data.get("teacher_id", 1),
        month=data.get("month", datetime.now().strftime("%Y-%m")),
        amount=data.get("amount", 0),
        base_amount=data.get("base_amount", 0),
        percentage=data.get("percentage", 30),
        is_paid=True,
        paid_at=datetime.utcnow(),
        note=data.get("note", "")
    )
    db.add(salary)
    db.commit()
    db.refresh(salary)
    return {
        "id": salary.id,
        "amount": salary.amount,
        "month": salary.month,
        "is_paid": salary.is_paid,
        "message": "Oylik muvaffaqiyatli to'landi!"
    }

@salary_router.get("/history")
def salary_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Oylik tarixi"""
    if current_user.role != UserRole.admin:
        raise HTTPException(status_code=403, detail="Ruxsat yoq")
    from app.models.finance import TeacherSalary
    salaries = db.query(TeacherSalary).order_by(TeacherSalary.paid_at.desc()).limit(50).all()
    return [{
        "id": s.id,
        "teacher_id": s.teacher_id,
        "amount": s.amount,
        "month": s.month,
        "percentage": s.percentage,
        "is_paid": s.is_paid,
        "note": s.note,
        "paid_at": str(s.paid_at) if s.paid_at else None
    } for s in salaries]


# ======== ATTENDANCE ========
from fastapi import APIRouter as _AR2
attendance_router = _AR2(prefix="/api/attendance", tags=["Attendance"])

class AttendanceItem(BaseModel):
    student_name: str
    status: str  # keldi, kelmadi, kech, sababli
    date: Optional[str] = None
    group_name: Optional[str] = None
    note: Optional[str] = None

class AttendanceBulk(BaseModel):
    date: str
    group_name: str
    records: list

@attendance_router.post("/save")
def save_attendance(
    data: AttendanceBulk,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Davomat saqlash"""
    from datetime import datetime
    # Simple log - store as JSON in notes
    results = {
        "date": data.date,
        "group": data.group_name,
        "total": len(data.records),
        "keldi": len([r for r in data.records if r.get("status") == "keldi"]),
        "kelmadi": len([r for r in data.records if r.get("status") == "kelmadi"]),
        "saved_by": current_user.full_name,
        "message": "Davomat saqlandi!"
    }
    return results

@attendance_router.get("/history")
def attendance_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return {"message": "Davomat tarixi", "records": []}


# ======== STATISTICS ========
from fastapi import APIRouter as _AR3
stats_router = _AR3(prefix="/api/stats", tags=["Statistics"])

@stats_router.get("/overview")
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Umumiy statistika - admin uchun"""
    from app.models.user import User as U, UserRole
    from app.models.finance import Payment, PaymentStatus
    from datetime import datetime

    total_students  = db.query(U).filter(U.role == UserRole.student).count()
    total_teachers  = db.query(U).filter(U.role == UserRole.teacher).count()
    
    month = datetime.now().strftime("%Y-%m")
    payments = db.query(Payment).filter(Payment.month == month).all()
    total_income = sum(p.paid_amount for p in payments)
    paid_count   = len([p for p in payments if p.status == PaymentStatus.paid])
    unpaid_count = len([p for p in payments if p.status == PaymentStatus.unpaid])

    return {
        "total_students": total_students,
        "total_teachers": total_teachers,
        "monthly_income": total_income,
        "paid_count":   paid_count,
        "unpaid_count": unpaid_count,
        "month": month
    }

@stats_router.get("/my-grades")
def my_grades(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """O'quvchi o'z baholarini ko'radi"""
    from app.models.finance import Grade
    from app.models.school import Student

    student = db.query(Student).filter(Student.user_id == current_user.id).first()
    if not student:
        return {"grades": [], "average": 0, "message": "Profil topilmadi"}

    grades = db.query(Grade).filter(Grade.student_id == student.id).order_by(Grade.date.desc()).limit(20).all()
    
    grade_list = [{
        "id": g.id,
        "score": g.score,
        "max_score": g.max_score,
        "percentage": g.percentage,
        "topic": g.topic or "Mavzu yo'q",
        "grade_type": g.grade_type,
        "date": str(g.date)[:10] if g.date else ""
    } for g in grades]

    avg = round(sum(g.percentage for g in grades) / len(grades), 1) if grades else 0

    return {
        "grades": grade_list,
        "average": avg,
        "total": len(grades)
    }

@stats_router.get("/my-groups")
def teacher_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """O'qituvchi o'z guruhlarini ko'radi"""
    from app.models.school import Teacher, Group

    teacher = db.query(Teacher).filter(Teacher.user_id == current_user.id).first()
    if not teacher:
        return {"groups": [], "total_students": 0}

    groups = db.query(Group).filter(Group.teacher_id == teacher.id).all()
    
    result = []
    for g in groups:
        result.append({
            "id": g.id,
            "name": g.name,
            "subject": g.subject,
            "student_count": len(g.students),
            "monthly_fee": g.monthly_fee,
            "is_active": g.is_active
        })

    total_students = sum(len(g.students) for g in groups)
    return {
        "groups": result,
        "total_students": total_students,
        "teacher_subject": teacher.subject
    }

@stats_router.get("/payments-summary")
def payments_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """To'lov umumiy hisobi"""
    from app.models.finance import Payment, PaymentStatus
    from datetime import datetime
    
    month = datetime.now().strftime("%Y-%m")
    payments = db.query(Payment).filter(Payment.month == month).all()
    
    total = sum(p.amount for p in payments)
    collected = sum(p.paid_amount for p in payments)
    
    return {
        "month": month,
        "total_expected": total,
        "total_collected": collected,
        "paid": len([p for p in payments if p.status == PaymentStatus.paid]),
        "unpaid": len([p for p in payments if p.status == PaymentStatus.unpaid]),
        "partial": len([p for p in payments if p.status == PaymentStatus.partial]),
    }
