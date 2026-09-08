from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

# Промежуточная таблица для связи учеников и групп (многие ко многим)
student_groups = Table(
    "student_groups",
    Base.metadata,
    Column("student_id", Integer, ForeignKey("students.id", ondelete="CASCADE"), primary_key=True),
    Column("group_id", Integer, ForeignKey("groups.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    role = Column(String, nullable=False, default="teacher")  # "teacher" или "student"
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=True)

    student = relationship("Student", back_populates="user_account")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=True)
    due_date = Column(String, nullable=False)
    color = Column(String, default="#6c5ce7")
    student_id = Column(Integer, ForeignKey("students.id", ondelete="SET NULL"), nullable=True)

    student = relationship("Student")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    age = Column(String, nullable=True)
    contacts = Column(String, nullable=True)

    grades = relationship("Grade", back_populates="student", cascade="all, delete-orphan")
    attendances = relationship("Attendance", back_populates="student", cascade="all, delete-orphan")
    user_account = relationship(
        "User", back_populates="student", uselist=False,
        cascade="all, delete-orphan", single_parent=True
    )
    groups = relationship("Group", secondary=student_groups, back_populates="students")

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)

    students = relationship("Student", secondary=student_groups, back_populates="groups")
    lessons = relationship(
        "Lesson", back_populates="group",
        cascade="all, delete-orphan", order_by="Lesson.date, Lesson.time"
    )

class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("group_id", "date", "time", name="uq_lesson_group_date_time"),)

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id", ondelete="CASCADE"), nullable=False)
    date = Column(String, nullable=False)  # ГГГГ-ММ-ДД
    time = Column(String, nullable=False)  # ЧЧ:ММ
    topic = Column(String, nullable=True)

    group = relationship("Group", back_populates="lessons")
    attendances = relationship("Attendance", back_populates="lesson", cascade="all, delete-orphan")

class Attendance(Base):
    __tablename__ = "attendances"
    __table_args__ = (UniqueConstraint("lesson_id", "student_id", name="uq_attendance_lesson_student"),)

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lessons.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="present")  # present / absent / late

    lesson = relationship("Lesson", back_populates="attendances")
    student = relationship("Student", back_populates="attendances")

class Grade(Base):
    __tablename__ = "grades"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    test_name = Column(String, nullable=False)
    score = Column(Integer, nullable=False)
    max_score = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="grades")