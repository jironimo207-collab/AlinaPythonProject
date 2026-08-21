import os
import re
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
import bcrypt
from database import engine, get_db, Base
import models

Base.metadata.create_all(bind=engine)

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
TIME_SLOTS = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")

def init_teacher_user():
    db = next(get_db())
    teacher_user = os.getenv("TEACHER_USERNAME", "alina")
    teacher_pass = os.getenv("TEACHER_PASSWORD", "teacher123")

    user = db.query(models.User).filter(models.User.username == teacher_user).first()
    if not user:
        new_user = models.User(
            username=teacher_user,
            hashed_password=hash_password(teacher_pass),
            full_name="Преподаватель",
            role="teacher"
        )
        db.add(new_user)
        db.commit()
    db.close()

@app.on_event("startup")
def on_startup():
    init_teacher_user()

def get_current_user_from_cookie(request: Request, db: Session):
    username = request.cookies.get("user")
    if not username:
        return None
    return db.query(models.User).filter(models.User.username == username).first()

def is_teacher_user(user) -> bool:
    return bool(user) and user.role == "teacher"

def is_student_user(user) -> bool:
    return bool(user) and user.role == "student"

@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/schedule")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    username = (username or "").strip()
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(request=request, name="login.html", context={"error": "Неверный логин или пароль"})

    target_url = "/my" if user.role == "student" else "/schedule"
    response = RedirectResponse(url=target_url, status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(key="user", value=user.username, httponly=True, samesite="lax", max_age=3600 * 24 * 7)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("user")
    return response

@app.get("/schedule", response_class=HTMLResponse)
async def get_schedule(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if is_student_user(user):
        return RedirectResponse(url="/my", status_code=status.HTTP_303_SEE_OTHER)

    teacher_mode = is_teacher_user(user)
    tasks = db.query(models.Task).all()

    return templates.TemplateResponse(
        request=request,
        name="schedule.html",
        context={
            "user": user,
            "is_teacher": teacher_mode,
            "teacher_name": user.full_name if user else "Гость",
            "tasks": tasks,
            "days": DAYS_OF_WEEK,
            "time_slots": TIME_SLOTS,
            "error": None
        }
    )

@app.post("/schedule/add")
async def add_lesson(
    request: Request,
    title: str = Form(...),
    day: str = Form(...),
    time_slot: str = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    due_date = f"{day} {time_slot}"
    new_task = models.Task(title=title.strip(), due_date=due_date, color="#6c5ce7")
    db.add(new_task)
    db.commit()
    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/schedule/delete/{task_id}")
async def delete_lesson(task_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)

# СТРОГАЯ ЗАЩИТА: ТОЛЬКО УЧИТЕЛЬ ВИДИТ УЧЕНИКОВ
@app.get("/students", response_class=HTMLResponse)
async def get_students(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    students = db.query(models.Student).options(
        joinedload(models.Student.grades),
        joinedload(models.Student.user_account)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={"students": students, "is_teacher": True, "teacher_name": user.full_name, "error": None}
    )

@app.post("/students/add")
async def add_student(
    request: Request,
    name: str = Form(...),
    username: str = Form(...),
    password: str = Form(...),
    age: str = Form(None),
    contacts: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    name, username = name.strip(), username.strip()
    if db.query(models.User).filter(models.User.username == username).first():
        students = db.query(models.Student).options(joinedload(models.Student.grades), joinedload(models.Student.user_account)).all()
        return templates.TemplateResponse(request=request, name="students.html", context={"students": students, "is_teacher": True, "teacher_name": user.full_name, "error": "Логин уже занят!"})

    new_student = models.Student(name=name, age=age, contacts=contacts)
    db.add(new_student)
    db.flush()

    new_account = models.User(
        username=username,
        hashed_password=hash_password(password),
        full_name=name,
        role="student",
        student_id=new_student.id
    )
    db.add(new_account)
    db.commit()
    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/students/edit/{student_id}")
async def edit_student(
    student_id: int,
    request: Request,
    name: str = Form(...),
    age: str = Form(None),
    contacts: str = Form(None),
    password: str = Form(None),
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student:
        student.name = name.strip()
        student.age = age
        student.contacts = contacts
        if student.user_account:
            student.user_account.full_name = name.strip()
            if password and len(password.strip()) > 0:
                student.user_account.hashed_password = hash_password(password.strip())
        db.commit()
    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/students/delete/{student_id}")
async def delete_student(student_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if student:
        db.delete(student)
        db.commit()
    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/students/{student_id}/grades/add")
async def add_grade(
    student_id: int,
    request: Request,
    test_name: str = Form(...),
    score: int = Form(...),
    max_score: int = Form(...),
    db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    new_grade = models.Grade(student_id=student_id, test_name=test_name.strip(), score=score, max_score=max_score)
    db.add(new_grade)
    db.commit()
    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/my", response_class=HTMLResponse)
async def my_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not is_student_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    student = db.query(models.Student).options(joinedload(models.Student.grades)).filter(models.Student.id == user.student_id).first()
    if not student:
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie("user")
        return response

    return templates.TemplateResponse(request=request, name="my.html", context={"student": student, "days": DAYS_OF_WEEK, "time_slots": TIME_SLOTS})