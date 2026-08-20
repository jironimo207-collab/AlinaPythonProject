import os
from fastapi import FastAPI, Request, Form, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session, joinedload
from database import engine, get_db, Base
import models

Base.metadata.create_all(bind=engine)

app = FastAPI()

templates = Jinja2Templates(directory="templates")

DAYS_OF_WEEK = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
TIME_SLOTS = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00", "18:00", "19:00"]

def init_teacher_user():
    db = next(get_db())
    # Читаем именно TEACHER_USERNAME и TEACHER_PASSWORD
    teacher_user = os.getenv("TEACHER_USERNAME", "alina")
    teacher_pass = os.getenv("TEACHER_PASSWORD", "teacher123")

    user = db.query(models.User).filter(models.User.username == teacher_user).first()
    if not user:
        new_user = models.User(
            username=teacher_user,
            hashed_password=teacher_pass,
            full_name="Преподаватель"
        )
        db.add(new_user)
        db.commit()
        print(f"--- [УСПЕХ] Пользователь {teacher_user} создан! ---")
    else:
        user.hashed_password = teacher_pass
        db.commit()
        print(f"--- [УСПЕХ] Пароль для {teacher_user} обновлен! ---")
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
    user = db.query(models.User).filter(models.User.username == username).first()

    if not user or user.hashed_password != password:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "Неверный логин или пароль"}
        )

    response = RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)

    # Исправление куки для работы на HTTPS (Render)
    response.set_cookie(
        key="user",
        value=user.username,
        httponly=True,
        samesite="lax",
        secure=True,
        max_age=3600 * 24 * 7  # Сохраняем на 7 дней
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
    tasks = db.query(models.Task).all()

    return templates.TemplateResponse(
        request=request,
        name="schedule.html",
        context={
            "teacher_name": user.full_name if user else "Гость",
            "tasks": tasks
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
        db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    due_date = f"{day} {time_slot}"
    new_task = models.Task(
        title=title,
        description=description,
        due_date=due_date,
        color=color
    )
    db.add(new_task)
    db.commit()
    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/schedule/delete/{task_id}")
async def delete_lesson(
        task_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    task = db.query(models.Task).filter(models.Task.id == task_id).first()
    if task:
        db.delete(task)
        db.commit()
    return RedirectResponse(url="/schedule", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/students", response_class=HTMLResponse)
async def get_students(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    students = db.query(models.Student).options(joinedload(models.Student.grades)).all()

    return templates.TemplateResponse(
        request=request,
        name="students.html",
        context={
            "students": students,
            "is_teacher": bool(user),
            "teacher_name": user.full_name if user else "Гость"
        }
    )


@app.post("/students/add")
async def add_student(
        request: Request,
        name: str = Form(...),
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
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    new_student = models.Student(
        name=name,
        age=age,
        branch=branch,
        category=category,
        subject=subject,
        group_name=group_name,
        request_date=request_date,
        visit_date=visit_date,
        contacts=contacts
    )
    db.add(new_student)
    db.commit()
    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/students/delete/{student_id}")
async def delete_student(
        student_id: int,
        request: Request,
        db: Session = Depends(get_db)
):
    user = get_current_user_from_cookie(request, db)
    if not user:
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
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)

    student = db.query(models.Student).filter(models.Student.id == student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Ученик не найден")

    new_grade = models.Grade(
        student_id=student_id,
        test_name=test_name,
        score=score,
        max_score=max_score
    )
    db.add(new_grade)
    db.commit()
    return RedirectResponse(url="/students", status_code=status.HTTP_303_SEE_OTHER)