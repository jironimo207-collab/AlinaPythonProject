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
    # Роль аккаунта: "teacher" (учитель, полный доступ) или "student" (ученик, только своя страница)
    role = Column(String, nullable=False, default="teacher")
    # Если роль "student" — ссылка на карточку ученика, к которой привязан этот логин
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True)

    student = relationship("Student", back_populates="user_account")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(String, nullable=False)
    color = Column(String, default="#a29bfe")
    # Ученик, к которому привязано занятие (для показа личного расписания ученику)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)

    student = relationship("Student")

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
    # Аккаунт ученика для входа на сайт (создаётся учителем, удаляется вместе с учеником)
    user_account = relationship(
        "User", back_populates="student", uselist=False,
        cascade="all, delete-orphan", single_parent=True
    )

class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    test_name = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, default=100)
    descriptor = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="grades")