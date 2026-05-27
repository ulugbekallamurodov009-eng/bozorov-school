from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

# Ko'p-ko'p: o'quvchi <-> guruh
student_group = Table(
    "student_group",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id")),
    Column("group_id",   Integer, ForeignKey("groups.id")),
)

class Teacher(Base):
    __tablename__ = "teachers"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), unique=True)
    subject    = Column(String, nullable=False)
    salary_pct = Column(Float, default=30.0)   # Foizli oylik
    salary_fix = Column(Float, default=0.0)    # Belgilangan oylik
    salary_type= Column(String, default="pct") # pct | fixed | hour
    hour_rate  = Column(Float, default=20000.0)# Soatbay narx
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user   = relationship("User", back_populates="teacher_profile")
    groups = relationship("Group", back_populates="teacher")


class Group(Base):
    __tablename__ = "groups"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    subject     = Column(String, nullable=False)
    teacher_id  = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    room        = Column(String, nullable=True)
    schedule    = Column(String, nullable=True)  # JSON string
    monthly_fee = Column(Float, default=300000.0)
    max_students= Column(Integer, default=15)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    teacher  = relationship("Teacher", back_populates="groups")
    students = relationship("Student", secondary=student_group, back_populates="groups")


class Student(Base):
    __tablename__ = "students"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user   = relationship("User", back_populates="student_profile")
    groups = relationship("Group", secondary=student_group, back_populates="students")
    grades = relationship("Grade", back_populates="student")
    payments = relationship("Payment", back_populates="student")
