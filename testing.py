from playwright.sync_api import page, expect

BASE_URL = "http://127.0.0.1:8001"


def test_01_teacher_login_and_schedule(page):
    # Тест входа преподавателя и перехода к расписанию
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "alina")
    page.fill("input[name='password']", "teacher123")
    page.click("button[type='submit']")

    expect(page).to_have_url(f"{BASE_URL}/schedule")
    # Проверяем наличие кнопки добавления урока
    expect(page.locator("button[data-bs-target='#addLessonModal']")).to_be_visible()


def test_02_add_and_delete_lesson(page):
    # Тест добавления и удаления урока в расписании
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "alina")
    page.fill("input[name='password']", "teacher123")
    page.click("button[type='submit']")

    # Открываем модальное окно добавления урока
    page.click("button[data-bs-target='#addLessonModal']")

    # Заполняем форму урока
    page.fill("input[name='title']", "Автотест Предмет")
    page.select_option("select[name='day']", "Понедельник")
    page.select_option("select[name='time_slot']", "09:00")
    page.select_option("select[name='color']", "#70a1ff")

    # Сохраняем урок (кнопка сохранения в модальном окне добавления занятия)
    page.locator("#addLessonModal button[type='submit']").click()

    # Проверяем, что урок появился в расписании
    expect(page.locator("text=Автотест Предмет")).to_be_visible()

    # Удаляем созданный урок
    page.locator(".task-card:has-text('Автотест Предмет') button.btn-delete").click()
    expect(page.locator("text=Автотест Предмет")).not_to_be_visible()


def test_03_add_student(page):
    # Тест добавления нового ученика
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "alina")
    page.fill("input[name='password']", "teacher123")
    page.click("button[type='submit']")

    # Переходим на страницу учеников
    page.click("a[href='/students']")
    expect(page).to_have_url(f"{BASE_URL}/students")

    # Открываем модальное окно создания ученика
    page.click("button[data-bs-target='#addStudentModal']")

    # Заполняем данные ученика
    page.fill("input[name='name']", "Иван Тестов")
    page.fill("input[name='username']", "ivan_test")
    page.fill("input[name='password']", "student123")
    page.fill("input[name='age']", "15")
    page.fill("input[name='contacts']", "+77001234567")

    # Сохраняем ученика
    page.locator("#addStudentModal button[type='submit']").click()

    # Проверяем, что ученик появился в таблице
    expect(page.locator("text=Иван Тестов")).to_be_visible()


def test_04_add_and_delete_grade(page):
    # Тест выставления и удаления оценки ученику
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "alina")
    page.fill("input[name='password']", "teacher123")
    page.click("button[type='submit']")

    page.click("a[href='/students']")

    # Находим строку с нашим тестовым учеником и жмем "+ Оценка"
    row = page.locator("tr:has-text('Иван Тестов')")
    row.locator("button:has-text('+ Оценка')").click()

    # Заполняем форму оценки в модальном окне
    modal = page.locator("[id^='addGradeModal']")
    modal.locator("input[name='test_name']").fill("Контрольная работа")
    modal.locator("input[name='score']").fill("9")
    modal.locator("input[name='max_score']").fill("10")
    modal.locator("button[type='submit']").click()

    # Проверяем, что оценка отобразилась у ученика
    expect(row.locator("text=9/10")).to_be_visible()

    # Открываем историю оценок (клик на значок оценки)
    row.locator(".grade-badge-clickable").click()

    # Удаляем оценку в истории
    history_modal = page.locator("[id^='historyModal']")
    history_modal.locator("form[action*='/students/grades/delete/'] button[type='submit']").click()

    # Закрываем модальное окно истории
    history_modal.locator("button[data-bs-dismiss='modal']").click()


def test_05_student_login_and_view_grades(page):
    # Тест входа под учеником и проверки его оценок/расписания
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "ivan_test")
    page.fill("input[name='password']", "student123")
    page.click("button[type='submit']")

    # Ученика по умолчанию перенаправляет на /my или /schedule
    # Проверим страницу оценок ученика
    page.goto(f"{BASE_URL}/my")
    expect(page).to_have_url(f"{BASE_URL}/my")
    expect(page.locator("text=Успеваемость: Иван Тестов")).to_be_visible()

    # Проверим, что расписание тоже открывается для ученика
    page.goto(f"{BASE_URL}/schedule")
    expect(page).to_have_url(f"{BASE_URL}/schedule")