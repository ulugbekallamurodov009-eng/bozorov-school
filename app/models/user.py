from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class UserRole(str, enum.Enum):
    admin        = "admin"
    teacher      = "teacher"
    student      = "student"
    receptionist = "receptionist"

class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    login      = Column(String, unique=True, index=True, nullable=False)
    password   = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name  = Column(String, nullable=False)
    phone      = Column(String, nullable=True)
    role       = Column(Enum(UserRole), default=UserRole.student, nullable=False)
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Aloqalar
    teacher_profile = relationship("Teacher", back_populates="user", uselist=False)
    student_profile = relationship("Student", back_populates="user", uselist=False)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def __repr__(self):
        return f"<User {self.login} ({self.role})>"
