import os
import re
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from passlib.context import CryptContext
from database import engine, get_db, Base
import models

Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
TIME_SLOTS = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]

# --- Хэширование паролей (требуется пакет: pip install "passlib[bcrypt]") ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        return False


USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


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
        print(f"--- [УСПЕХ] Создан пользователь: {teacher_user} ---")
    else:
        user.hashed_password = hash_password(teacher_pass)
        user.role = "teacher"
        db.commit()
        print(f"--- [УСПЕХ] Пароль обновлен для: {teacher_user} ---")
    db.close()


@app.on_event("startup")
def on_startup():
    init_teacher_user()


def get_current_user_from_cookie(request: Request, db: Session):
    username = request.cookies.get("user")
    if not username:
        return None
    user = db.query(models.User).filter(models.User.username == username).first()
    return user


def is_teacher_user(user) -> bool:
    return bool(user) and user.role == "teacher"


def is_student_user(user) -> bool:
    return bool(user) and user.role == "student"


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/schedule")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"error": None}
    )


@app.post("/login", response_class=HTMLResponse)
async def login(
        request: Request,
        username: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    username = (username or "").strip()

    if not username or not password:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Введите логин и пароль"}
        )

    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Неверный логин или пароль"}
        )

    target_url = "/my" if user.role == "student" else "/schedule"
    response = RedirectResponse(url=target_url, status_code=status.HTTP_303_SEE_OTHER)

    response.set_cookie(
        key="user",
        value=user.username,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=3600 * 24 * 7
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie("user")
    return response


@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        request=request,
        name="profile.html",
        context={"user": user, "teacher_name": user.full_name}
    )


@app.get("/schedule", response_class=HTMLResponse)
async def get_schedule(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)

    if is_student_user(user):
        return RedirectResponse(url="/my", status_code=status.HTTP_303_SEE_OTHER)

    teacher_mode = is_teacher_user(user)
    tasks = db.query(models.Task).all()
    students = db.query(models.Student).all() if teacher_mode else []

    return templates.TemplateResponse(
        request=request,
        name="schedule.html",
        context={
            "user": user,
            "is_teacher": teacher_mode,
            "teacher_name": user.full_name if user else "Гость",
            "tasks": tasks,
            "students": students,
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
        color: str = Form(...),
        description: str = Form(None),
        student_id: int = Form(None),
        score: int = Form(None),
        descriptor: str = Form(None),
        db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    title = (title or "").strip()
    errors = []

    if not title:
        errors.append("Введите название занятия.")
    if day not in DAYS_OF_WEEK:
        errors.append("Некорректный день недели.")
    if time_slot not in TIME_SLOTS:
        errors.append("Некорректное время занятия.")
    if not HEX_COLOR_RE.match(color or ""):
        errors.append("Некорректный цвет карточки.")
    if score is not None and not (0 <= score <= 100):
        errors.append("Оценка должна быть числом от 0 до 100.")

    student = None
    if student_id:
        student = db.query(models.Student).filter(models.Student.id == student_id).first()
        if not student:
            errors.append("Выбранный ученик не найден.")

    if errors:
        tasks = db.query(models.Task).all()
        students = db.query(models.Student).all()
        return templates.TemplateResponse(
            request=request,
            name="schedule.html",
            context={
                "user": user,
                "is_teacher": True,
                "teacher_name": user.full_name,
                "tasks": tasks,
                "students": students,
                "days": DAYS_OF_WEEK,
                "time_slots": TIME_SLOTS,
                "error": " ".join(errors)
            }
        )

    due_date = f"{day} {time_slot}"
    new_task = models.Task(
        title=title,
        description=description,
        due_date=due_date,
        color=color,
        student_id=student.id if student else None
    )
    db.add(new_task)

    if student and score is not None:
        grade_entry = models.Grade(
            student_id=student.id,
            test_name=title,
            score=score,
            max_score=100,
            descriptor=descriptor
        )
        db.add(grade_entry)

    db.commit()
    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/schedule/delete/{task_id}")
async def delete_lesson(
        task_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/students", response_class=HTMLResponse)
async def get_students(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    students = db.query(models.Student).options(
        joinedload(models.Student.grades), joinedload(models.Student.user_account)
    ).all()

    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "students": students,
            "is_teacher": True,
            "teacher_name": user.full_name,
            "error": None
        }
    )


@app.post("/students/add")
async def add_student(
        request: Request,
        name: str = Form(...),
        username: str = Form(...),
        password: str = Form(...),
        age: str = Form(None),
        branch: str = Form(None),
        category: str = Form(None),
        subject: str = Form(None),
        group_name: str = Form(None),
        request_date: str = Form(None),
        visit_date: str = Form(None),
        contacts: str = Form(None),
        db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    name = (name or "").strip()
    username = (username or "").strip()
    age = (age or "").strip()
    errors = []

    if not name:
        errors.append("Введите ФИО ученика.")
    if not USERNAME_RE.match(username):
        errors.append("Логин должен быть длиной 3-32 символа и содержать только латинские буквы, цифры, '.', '_' или '-'.")
    elif db.query(models.User).filter(models.User.username == username).first():
        errors.append("Такой логин уже занят, выберите другой.")
    if len(password) < 6:
        errors.append("Пароль должен содержать не менее 6 символов.")
    if age and not age.isdigit():
        errors.append("Возраст должен быть числом.")

    if errors:
        students = db.query(models.Student).options(
            joinedload(models.Student.grades), joinedload(models.Student.user_account)
        ).all()
        return templates.TemplateResponse(
            request=request,
            name="students.html",
            context={
                "students": students,
                "is_teacher": True,
                "teacher_name": user.full_name,
                "error": " ".join(errors)
            }
        )

    new_student = models.Student(
        name=name,
        age=age or None,
        branch=branch,
        category=category,
        subject=subject,
        group_name=group_name,
        request_date=request_date,
        visit_date=visit_date,
        contacts=contacts
    )
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


@app.post("/students/delete/{student_id}")
async def delete_student(
        student_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
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
        max_score: int = Form(100),
        db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not is_teacher_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")

    test_name = (test_name or "").strip()
    errors = []
    if not test_name:
        errors.append("Введите название теста/работы.")
    if max_score <= 0:
        errors.append("Максимальный балл должен быть больше нуля.")
    if not (0 <= score <= max_score):
        errors.append(f"Оценка должна быть в диапазоне от 0 до {max_score}.")

    if errors:
        students = db.query(models.Student).options(
            joinedload(models.Student.grades), joinedload(models.Student.user_account)
        ).all()
        return templates.TemplateResponse(
            request=request,
            name="students.html",
            context={
                "students": students,
                "is_teacher": True,
                "teacher_name": user.full_name,
                "error": " ".join(errors)
            }
        )

    new_grade = models.Grade(
        student_id=student_id,
        test_name=test_name,
        score=score,
        max_score=max_score
    )
    db.add(new_grade)
    db.commit()
    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/my", response_class=HTMLResponse)
async def my_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not is_student_user(user):
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    student = db.query(models.Student).options(
        joinedload(models.Student.grades)
    ).filter(models.Student.id == user.student_id).first()

    if not student:
        response = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
        response.delete_cookie("user")
        return response

    my_tasks = db.query(models.Task).filter(models.Task.student_id == student.id).all()

    return templates.TemplateResponse(
        request=request,
        name="my.html",
        context={
            "student": student,
            "tasks": my_tasks,
            "days": DAYS_OF_WEEK,
            "time_slots": TIME_SLOTS
        }
    )