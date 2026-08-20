from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(String, nullable=False)
    color = Column(String, default="#a29bfe")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    category = Column(String, nullable=True)
    subject = Column(String, nullable=True)
    group_name = Column(String, nullable=True)
    request_date = Column(String, nullable=True)
    visit_date = Column(String, nullable=True)
    contacts = Column(String, nullable=True)

    # Связь с оценками (при удалении ученика удаляются и его оценки)
    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")

class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    test_name = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="grades")