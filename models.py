from sqlalchemy import Column, Integer, String
from database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    due_date = Column(String)
    description = Column(String, nullable=True)
    color = Column(String, default="#a29bfe")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)                # ФИО
    age = Column(String, nullable=True)               # Возраст
    branch = Column(String, default="Рудный")         # Филиалы
    category = Column(String, nullable=True)         # Категория
    subject = Column(String, nullable=True)          # Дисциплины
    group_name = Column(String, nullable=True)       # Группа
    request_date = Column(String, nullable=True)     # Дата / тип обращения
    visit_date = Column(String, nullable=True)       # Дата визита
    contacts = Column(String, nullable=True)         # Контакты