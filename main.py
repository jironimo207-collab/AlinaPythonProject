import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Depends, Form, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

import models
from database import engine, get_db

# Загружаем переменные из .env
load_dotenv()

# Читаем секретные данные из переменных окружения
SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-change-me")
TEACHER_USERNAME = os.getenv("TEACHER_USERNAME", "alina")
TEACHER_PASSWORD = os.getenv("TEACHER_PASSWORD", "teacher123")

models.Base.metadata.create_all(bind=engine)

os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

app = FastAPI()

# Используем секретный ключ из .env
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def is_teacher(request: Request) -> bool:
    return request.session.get("is_teacher", False)


@app.get("/")
async def root():
    return RedirectResponse(url="/schedule")


# --- РАСПИСАНИЕ И УРОКИ ---

@app.get("/schedule")
async def get_schedule(request: Request, db: Session = Depends(get_db)):
    try:
        raw_tasks = db.query(models.Task).all()
    except Exception:
        raw_tasks = []

    tasks = []
    for task in raw_tasks:
        tasks.append({
            "id": getattr(task, "id", None),
            "title": getattr(task, "title", ""),
            "due_date": str(getattr(task, "due_date", "")),
            "description": getattr(task, "description", ""),
            "color": getattr(task, "color", "#a29bfe")
        })

    time_slots = ["9:00-10:30", "10:30-12:00", "12:00-15:30", "15:30-17:00", "17:00-18:30"]
    days_of_week = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]

    return templates.TemplateResponse(
        request=request,
        name="schedule.html",
        context={
            "tasks": tasks,
            "time_slots": time_slots,
            "days_of_week": days_of_week,
            "is_teacher": is_teacher(request),
            "teacher_name": request.session.get("user_name", "Фурсова Алина Евгеньевна")
        }
    )


@app.post("/schedule/add")
async def add_task(
    request: Request,
    title: str = Form(...),
    day: str = Form(...),
    time_slot: str = Form(...),
    description: Optional[str] = Form(None),
    color: str = Form("#ff7675"),
    db: Session = Depends(get_db)
):
    if not is_teacher(request):
        raise HTTPException(status_code=403, detail="Доступ только для учителя")

    schedule_time_label = f"{day} {time_slot}"

    new_task = models.Task(
        title=title,
        due_date=schedule_time_label,
        description=description,
        color=color
    )
    db.add(new_task)
    db.commit()

    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/schedule/delete/{task_id}")
async def delete_task(
    task_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    if not is_teacher(request):
        raise HTTPException(status_code=403, detail="Доступ только для учителя")

    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()

    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)


# --- УЧЕНИКИ ---

@app.get("/students")
async def get_students(request: Request, db: Session = Depends(get_db)):
    students = []
    if hasattr(models, "Student"):
        try:
            students = db.query(models.Student).all()
        except Exception:
            students = []

    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "students": students,
            "is_teacher": is_teacher(request),
            "teacher_name": request.session.get("user_name", "Фурсова Алина Евгеньевна")
        }
    )


@app.post("/students/add")
async def add_student(
    request: Request,
    name: str = Form(...),
    info: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    if not is_teacher(request):
        raise HTTPException(status_code=403, detail="Доступ только для учителя")

    if hasattr(models, "Student"):
        new_student = models.Student(name=name, info=info)
        db.add(new_student)
        db.commit()

    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/students/delete/{student_id}")
async def delete_student(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    if not is_teacher(request):
        raise HTTPException(status_code=403, detail="Доступ только для учителя")

    if hasattr(models, "Student"):
        student = db.query(models.Student).filter(models.Student.id == student_id).first()
        if student:
            db.delete(student)
            db.commit()

    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)


# --- АВТОРИЗАЦИЯ ---

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={})


@app.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    # Проверяем введенный логин и пароль через переменные из .env
    if username == TEACHER_USERNAME and password == TEACHER_PASSWORD:
        request.session["is_teacher"] = True
        request.session["user_name"] = "Фурсова Алина Евгеньевна"
        return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": "Неверный логин или пароль"}
    )


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)