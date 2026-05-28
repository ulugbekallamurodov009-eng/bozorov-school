from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class GradeType(str, enum.Enum):
    daily   = "daily"    # Kunlik
    weekly  = "weekly"   # Haftalik
    monthly = "monthly"  # Oylik

class PaymentStatus(str, enum.Enum):
    paid    = "paid"
    unpaid  = "unpaid"
    partial = "partial"

class Grade(Base):
    __tablename__ = "grades"

    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    group_id   = Column(Integer, ForeignKey("groups.id"),   nullable=False)
    score      = Column(Float, nullable=False)
    max_score  = Column(Float, default=30.0)
    topic      = Column(String, nullable=True)
    grade_type = Column(Enum(GradeType), default=GradeType.daily)
    note       = Column(String, nullable=True)
    date       = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="grades")

    @property
    def percentage(self):
        if self.max_score == 0:
            return 0
        return round(self.score / self.max_score * 100, 1)


class Payment(Base):
    __tablename__ = "payments"

    id         = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    group_id   = Column(Integer, ForeignKey("groups.id"),   nullable=False)
    amount     = Column(Float, nullable=False)
    paid_amount= Column(Float, default=0.0)
    month      = Column(String, nullable=False)  # "2026-06"
    status     = Column(Enum(PaymentStatus), default=PaymentStatus.unpaid)
    method     = Column(String, nullable=True)   # click, payme, uzcard, cash
    note       = Column(String, nullable=True)
    paid_at    = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    student = relationship("Student", back_populates="payments")

    @property
    def remaining(self):
        return self.amount - self.paid_amount


class TeacherSalary(Base):
    __tablename__ = "teacher_salaries"

    id         = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    month      = Column(String, nullable=False)  # "2026-06"
    amount     = Column(Float, nullable=False)
    base_amount= Column(Float, nullable=True)    # Asos summa
    percentage = Column(Float, nullable=True)    # Foiz
    is_paid    = Column(Boolean, default=False)
    paid_at    = Column(DateTime(timezone=True), nullable=True)
    note       = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
