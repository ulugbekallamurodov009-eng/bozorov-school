"""
Resepshn (Reception) Router
Ruxsat berilgan:
  - To'lov qabul qilish va ko'rish
  - Davomat belgilash va ko'rish
  - O'quvchilar ro'yxatini ko'rish (faqat o'qish)
  - Natijalar (baholar) ko'rish (faqat o'qish)
  - Qidiruv
  - Login yaratish (o'quvchi uchun)

Taqiqlangan:
  - Dars jadvali o'zgartirish
  - Oylik hisob
  - Xodimlar boshqaruvi
  - Sozlamalar
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, date
import random, string

from app.core.database import get_db
from app.core.security import get_current_user, hash_password
from app.models.user import User, UserRole
from app.models.school import Student, Teacher, Group
from app.models.finance import Grade, Payment, PaymentStatus

router = APIRouter(prefix="/api/reception", tags=["Reception"])


# ─────────────────────────────────────────────
# GUARD — faqat admin yoki resepshn kiradi
# ─────────────────────────────────────────────
def require_reception(current_user: User = Depends(get_current_user)):
    if current_user.role not in [UserRole.admin, UserRole.receptionist]:
        raise HTTPException(status_code=403, detail="Ruxsat yo'q")
    return current_user


# ─────────────────────────────────────────────
# SCHEMAS
# ─────────────────────────────────────────────

class StudentBrief(BaseModel):
    id: int
    user_id: int
    full_name: str
    phone: Optional[str]
    groups: List[str]
    payment_status: str  # paid | unpaid | partial | none
    payment_remaining: float

    class Config:
        from_attributes = True


class PaymentAcceptRequest(BaseModel):
    payment_id: int
    paid_amount: float
    method: str = "cash"   # cash | click | payme | uzcard
    note: Optional[str] = None


class PaymentCreateRequest(BaseModel):
    student_id: int
    group_id: int
    amount: float
    month: str            # "2026-06"
    method: str = "cash"
    note: Optional[str] = None


class PaymentOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    group_name: str
    amount: float
    paid_amount: float
    remaining: float
    month: str
    status: str
    method: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime


class AttendanceMarkRequest(BaseModel):
    student_id: int
    group_id: int
    is_present: bool = True
    date: Optional[str] = None   # "2026-05-27", bo'sh bo'lsa bugun
    note: Optional[str] = None


class AttendanceOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    group_id: int
    date: str
    is_present: bool
    note: Optional[str]


class CreateStudentLoginRequest(BaseModel):
    first_name: str
    last_name: str
    phone: Optional[str] = None
    group_id: Optional[int] = None


class LoginCreatedResponse(BaseModel):
    user_id: int
    login: str
    password_plain: str
    full_name: str


class GradeOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    score: float
    max_score: float
    percentage: float
    topic: Optional[str]
    grade_type: str
    date: datetime


class SearchResult(BaseModel):
    student_id: int
    user_id: int
    full_name: str
    phone: Optional[str]
    groups: List[str]
    payment_status: str


class DashboardStats(BaseModel):
    total_students: int
    paid_this_month: int
    unpaid_this_month: int
    partial_this_month: int
    total_expected: float
    total_collected: float
    today_attendance: int
    today_total: int
    today_percent: float
    recent_payments: List[dict]


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def current_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")


def get_student_payment_status(student: Student, month: str):
    """O'quvchining joriy oy to'lov holati"""
    payment = next((p for p in student.payments if p.month == month), None)
    if not payment:
        return "none", 0.0
    return payment.status, payment.remaining


def _payment_to_out(p: Payment, db: Session) -> dict:
    student = db.query(Student).options(joinedload(Student.user)).filter(Student.id == p.student_id).first()
    group = db.query(Group).filter(Group.id == p.group_id).first()
    return {
        "id": p.id,
        "student_id": p.student_id,
        "student_name": student.user.full_name if student else "Noma'lum",
        "group_name": group.name if group else "Noma'lum",
        "amount": p.amount,
        "paid_amount": p.paid_amount,
        "remaining": p.remaining,
        "month": p.month,
        "status": p.status,
        "method": p.method,
        "paid_at": p.paid_at,
        "created_at": p.created_at,
    }


# ─────────────────────────────────────────────
# 1. DASHBOARD STATISTIKA
# ─────────────────────────────────────────────

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Resepshn bosh sahifasi uchun statistika"""
    month = current_month()
    today_str = date.today().isoformat()

    all_students = db.query(Student).all()
    total_students = len(all_students)

    # To'lov statistikasi (joriy oy)
    month_payments = db.query(Payment).filter(Payment.month == month).all()
    paid_count    = sum(1 for p in month_payments if p.status == PaymentStatus.paid)
    unpaid_count  = sum(1 for p in month_payments if p.status == PaymentStatus.unpaid)
    partial_count = sum(1 for p in month_payments if p.status == PaymentStatus.partial)
    total_expected   = sum(p.amount for p in month_payments)
    total_collected  = sum(p.paid_amount for p in month_payments)

    # Bugungi davomat (attendance jadvali bo'lsa, agar yo'q bo'lsa 0)
    from app.models.finance import Attendance  # mavjud bo'lsa
    try:
        today_att = db.query(Attendance).filter(
            func.date(Attendance.date) == today_str
        ).all()
        today_present = sum(1 for a in today_att if a.is_present)
        today_total   = len(today_att)
        today_pct = round(today_present / today_total * 100, 1) if today_total else 0
    except Exception:
        today_present = 0
        today_total   = total_students
        today_pct     = 0

    # So'nggi 5 ta to'lov
    recent = db.query(Payment).filter(
        Payment.paid_at != None
    ).order_by(Payment.paid_at.desc()).limit(5).all()

    recent_list = []
    for p in recent:
        st = db.query(Student).options(joinedload(Student.user)).filter(Student.id == p.student_id).first()
        recent_list.append({
            "student_name": st.user.full_name if st else "?",
            "amount": p.paid_amount,
            "method": p.method,
            "paid_at": p.paid_at.isoformat() if p.paid_at else None,
        })

    return DashboardStats(
        total_students=total_students,
        paid_this_month=paid_count,
        unpaid_this_month=unpaid_count,
        partial_this_month=partial_count,
        total_expected=total_expected,
        total_collected=total_collected,
        today_attendance=today_present,
        today_total=today_total,
        today_percent=today_pct,
        recent_payments=recent_list,
    )


# ─────────────────────────────────────────────
# 2. O'QUVCHILAR (faqat ko'rish)
# ─────────────────────────────────────────────

@router.get("/students", response_model=List[StudentBrief])
def list_students(
    group_id: Optional[int] = None,
    payment_status: Optional[str] = None,   # paid | unpaid | partial | none
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """O'quvchilar ro'yxati — to'lov holati bilan"""
    month = current_month()

    query = db.query(Student).options(
        joinedload(Student.user),
        joinedload(Student.groups),
        joinedload(Student.payments)
    )
    if group_id:
        query = query.join(Student.groups).filter(Group.id == group_id)

    students = query.all()
    result = []
    for s in students:
        status, remaining = get_student_payment_status(s, month)
        if payment_status and status != payment_status:
            continue
        result.append(StudentBrief(
            id=s.id,
            user_id=s.user_id,
            full_name=s.user.full_name,
            phone=s.user.phone,
            groups=[g.name for g in s.groups],
            payment_status=status,
            payment_remaining=remaining,
        ))
    return result


@router.get("/students/{student_id}")
def get_student_detail(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Bitta o'quvchi to'liq ma'lumoti"""
    s = db.query(Student).options(
        joinedload(Student.user),
        joinedload(Student.groups),
        joinedload(Student.payments),
        joinedload(Student.grades)
    ).filter(Student.id == student_id).first()

    if not s:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")

    month = current_month()
    status, remaining = get_student_payment_status(s, month)

    return {
        "id": s.id,
        "user_id": s.user_id,
        "full_name": s.user.full_name,
        "phone": s.user.phone,
        "login": s.user.login,
        "is_active": s.user.is_active,
        "groups": [{"id": g.id, "name": g.name, "subject": g.subject, "monthly_fee": g.monthly_fee} for g in s.groups],
        "current_month_payment": {
            "status": status,
            "remaining": remaining,
        },
        "all_payments": [
            {"id": p.id, "month": p.month, "amount": p.amount,
             "paid_amount": p.paid_amount, "remaining": p.remaining,
             "status": p.status, "method": p.method, "paid_at": p.paid_at}
            for p in sorted(s.payments, key=lambda x: x.month, reverse=True)
        ],
        "recent_grades": [
            {"score": g.score, "max_score": g.max_score,
             "percentage": g.percentage, "topic": g.topic,
             "date": g.date}
            for g in sorted(s.grades, key=lambda x: x.date, reverse=True)[:10]
        ],
        "created_at": s.created_at,
    }


# ─────────────────────────────────────────────
# 3. TO'LOVLAR
# ─────────────────────────────────────────────

@router.get("/payments", response_model=List[dict])
def list_payments(
    month: Optional[str] = None,
    status: Optional[str] = None,
    student_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """To'lovlar ro'yxati"""
    query = db.query(Payment)
    if month:
        query = query.filter(Payment.month == month)
    if status:
        query = query.filter(Payment.status == status)
    if student_id:
        query = query.filter(Payment.student_id == student_id)

    payments = query.order_by(Payment.created_at.desc()).all()
    return [_payment_to_out(p, db) for p in payments]


@router.get("/payments/unpaid")
def get_unpaid(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """To'lamagan o'quvchilar"""
    m = month or current_month()
    payments = db.query(Payment).filter(
        Payment.month == m,
        Payment.status.in_([PaymentStatus.unpaid, PaymentStatus.partial])
    ).all()
    return [_payment_to_out(p, db) for p in payments]


@router.post("/payments/create")
def create_payment_record(
    data: PaymentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Yangi to'lov yozuvi yaratish"""
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
        note=data.note,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return _payment_to_out(payment, db)


@router.put("/payments/{payment_id}/accept")
def accept_payment(
    payment_id: int,
    data: PaymentAcceptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """To'lov qabul qilish — resepshn asosiy vazifasi"""
    p = db.query(Payment).filter(Payment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="To'lov topilmadi")

    p.paid_amount = data.paid_amount
    p.method = data.method
    if data.note:
        p.note = data.note

    if p.paid_amount >= p.amount:
        p.status = PaymentStatus.paid
        p.paid_at = datetime.utcnow()
    elif p.paid_amount > 0:
        p.status = PaymentStatus.partial
    else:
        p.status = PaymentStatus.unpaid

    db.commit()
    db.refresh(p)
    return _payment_to_out(p, db)


@router.get("/payments/summary")
def payment_summary(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Oylik to'lov hisoboti"""
    m = month or current_month()
    payments = db.query(Payment).filter(Payment.month == m).all()

    return {
        "month": m,
        "total_expected": sum(p.amount for p in payments),
        "total_collected": sum(p.paid_amount for p in payments),
        "total_remaining": sum(p.remaining for p in payments),
        "paid_count":    sum(1 for p in payments if p.status == PaymentStatus.paid),
        "unpaid_count":  sum(1 for p in payments if p.status == PaymentStatus.unpaid),
        "partial_count": sum(1 for p in payments if p.status == PaymentStatus.partial),
        "total_records": len(payments),
    }


# ─────────────────────────────────────────────
# 4. DAVOMAT
# ─────────────────────────────────────────────

@router.post("/attendance/mark")
def mark_attendance(
    data: AttendanceMarkRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Davomat belgilash"""
    from app.models.finance import Attendance

    att_date = date.fromisoformat(data.date) if data.date else date.today()

    # Bir xil kun + o'quvchi + guruh uchun qayta yozmaslik
    existing = db.query(Attendance).filter(
        Attendance.student_id == data.student_id,
        Attendance.group_id == data.group_id,
        func.date(Attendance.date) == att_date.isoformat()
    ).first()

    if existing:
        existing.is_present = data.is_present
        existing.note = data.note
        db.commit()
        db.refresh(existing)
        att = existing
    else:
        att = Attendance(
            student_id=data.student_id,
            group_id=data.group_id,
            date=datetime.combine(att_date, datetime.min.time()),
            is_present=data.is_present,
            note=data.note,
        )
        db.add(att)
        db.commit()
        db.refresh(att)

    student = db.query(Student).options(joinedload(Student.user)).filter(
        Student.id == data.student_id
    ).first()

    return {
        "id": att.id,
        "student_id": att.student_id,
        "student_name": student.user.full_name if student else "?",
        "group_id": att.group_id,
        "date": att.date.date().isoformat(),
        "is_present": att.is_present,
        "note": att.note,
    }


@router.get("/attendance/today")
def today_attendance(
    group_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Bugungi davomat"""
    from app.models.finance import Attendance
    today_str = date.today().isoformat()

    query = db.query(Attendance).filter(
        func.date(Attendance.date) == today_str
    )
    if group_id:
        query = query.filter(Attendance.group_id == group_id)

    records = query.all()
    result = []
    for a in records:
        st = db.query(Student).options(joinedload(Student.user)).filter(Student.id == a.student_id).first()
        result.append({
            "id": a.id,
            "student_id": a.student_id,
            "student_name": st.user.full_name if st else "?",
            "group_id": a.group_id,
            "date": today_str,
            "is_present": a.is_present,
            "note": a.note,
        })
    return result


@router.get("/attendance/student/{student_id}")
def student_attendance(
    student_id: int,
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Bitta o'quvchi davomati"""
    from app.models.finance import Attendance
    query = db.query(Attendance).filter(Attendance.student_id == student_id)
    if month:
        query = query.filter(func.strftime("%Y-%m", Attendance.date) == month)

    records = query.order_by(Attendance.date.desc()).all()
    present = sum(1 for a in records if a.is_present)
    absent  = sum(1 for a in records if not a.is_present)

    return {
        "student_id": student_id,
        "total_days": len(records),
        "present": present,
        "absent": absent,
        "percent": round(present / len(records) * 100, 1) if records else 0,
        "records": [
            {"id": a.id, "date": a.date.date().isoformat(),
             "is_present": a.is_present, "group_id": a.group_id, "note": a.note}
            for a in records
        ]
    }


# ─────────────────────────────────────────────
# 5. NATIJALAR (faqat ko'rish)
# ─────────────────────────────────────────────

@router.get("/grades/group/{group_id}")
def group_grades(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Guruh baholarini ko'rish"""
    grades = db.query(Grade).filter(Grade.group_id == group_id).all()
    result = []
    for g in grades:
        st = db.query(Student).options(joinedload(Student.user)).filter(Student.id == g.student_id).first()
        result.append({
            "id": g.id,
            "student_id": g.student_id,
            "student_name": st.user.full_name if st else "?",
            "score": g.score,
            "max_score": g.max_score,
            "percentage": g.percentage,
            "topic": g.topic,
            "grade_type": g.grade_type,
            "date": g.date,
        })
    return result


@router.get("/grades/student/{student_id}")
def student_grades(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Bitta o'quvchi baholarini ko'rish"""
    grades = db.query(Grade).filter(
        Grade.student_id == student_id
    ).order_by(Grade.date.desc()).all()

    if not grades:
        return {"student_id": student_id, "grades": [], "average": 0}

    avg = round(sum(g.percentage for g in grades) / len(grades), 1)
    return {
        "student_id": student_id,
        "average_percent": avg,
        "grades": [
            {"id": g.id, "score": g.score, "max_score": g.max_score,
             "percentage": g.percentage, "topic": g.topic,
             "grade_type": g.grade_type, "date": g.date}
            for g in grades
        ]
    }


# ─────────────────────────────────────────────
# 6. QIDIRUV
# ─────────────────────────────────────────────

@router.get("/search")
def search(
    q: str = Query(..., min_length=2, description="Ism, login yoki telefon"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """O'quvchi qidirish — ism, login yoki telefon bo'yicha"""
    q_lower = f"%{q.lower()}%"

    users = db.query(User).filter(
        User.role == UserRole.student,
        or_(
            func.lower(User.first_name).like(q_lower),
            func.lower(User.last_name).like(q_lower),
            func.lower(User.login).like(q_lower),
            User.phone.like(q_lower),
        )
    ).all()

    result = []
    month = current_month()
    for u in users:
        if not u.student_profile:
            continue
        s = u.student_profile
        status, _ = get_student_payment_status(s, month)
        result.append({
            "student_id": s.id,
            "user_id": u.id,
            "full_name": u.full_name,
            "login": u.login,
            "phone": u.phone,
            "groups": [g.name for g in s.groups],
            "payment_status": status,
        })
    return result


# ─────────────────────────────────────────────
# 7. LOGIN YARATISH (faqat o'quvchi uchun)
# ─────────────────────────────────────────────

@router.post("/create-student-login", response_model=LoginCreatedResponse)
def create_student_login(
    data: CreateStudentLoginRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Yangi o'quvchi uchun login va parol yaratish"""

    # Login generatsiya
    f = data.first_name.lower().replace(" ", "")[:5]
    num = random.randint(10, 99)
    base_login = f"{f}{num}"

    # Unique qilish
    login = base_login
    counter = 1
    while db.query(User).filter(User.login == login).first():
        login = f"{base_login}{counter}"
        counter += 1

    # Parol generatsiya
    chars = string.ascii_lowercase + string.digits
    plain_password = "".join(random.choices(chars, k=8))

    # User yaratish
    user = User(
        login=login,
        password=hash_password(plain_password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role=UserRole.student,
    )
    db.add(user)
    db.flush()

    # Student profil
    student = Student(user_id=user.id)
    db.add(student)
    db.flush()

    # Guruhga qo'shish
    if data.group_id:
        group = db.query(Group).filter(Group.id == data.group_id).first()
        if group:
            group.students.append(student)

    db.commit()

    return LoginCreatedResponse(
        user_id=user.id,
        login=login,
        password_plain=plain_password,
        full_name=user.full_name,
    )


# ─────────────────────────────────────────────
# 8. GURUHLAR (faqat ko'rish)
# ─────────────────────────────────────────────

@router.get("/groups")
def list_groups(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Barcha guruhlar — davomat va to'lov belgilash uchun"""
    groups = db.query(Group).filter(Group.is_active == True).all()
    result = []
    for g in groups:
        teacher_name = g.teacher.user.full_name if g.teacher and g.teacher.user else "Biriktirilmagan"
        result.append({
            "id": g.id,
            "name": g.name,
            "subject": g.subject,
            "teacher_name": teacher_name,
            "room": g.room,
            "schedule": g.schedule,
            "monthly_fee": g.monthly_fee,
            "student_count": len(g.students),
            "max_students": g.max_students,
        })
    return result


@router.get("/schedule")
def get_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reception)
):
    """Dars jadvali — faqat ko'rish (o'zgartirish taqiqlangan)"""
    groups = db.query(Group).filter(Group.is_active == True).all()
    schedule = []
    for g in groups:
        if g.schedule:
            schedule.append({
                "group_id": g.id,
                "group_name": g.name,
                "subject": g.subject,
                "teacher": g.teacher.user.full_name if g.teacher and g.teacher.user else "-",
                "room": g.room,
                "schedule": g.schedule,
            })
    return schedule
