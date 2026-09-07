from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8001"


def test_01_teacher_login_and_schedule(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "alina")
    page.fill("input[name='password']", "teacher123")
    page.click("button[type='submit']")

    expect(page).to_have_url(f"{BASE_URL}/schedule")
    expect(page.locator("button[data-bs-target='#addLessonModal']")).to_be_visible()


def test_02_add_and_delete_lesson(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "alina")
    page.fill("input[name='password']", "teacher123")
    page.click("button[type='submit']")

    # Возвращаем force=True, чтобы надежно перехватить клик по кнопке модалки
    page.locator("button[data-bs-target='#addLessonModal']").click(force=True)
    page.locator("#addLessonModal").wait_for(state="visible")

    page.fill("input[name='title']", "Автотест Предмет")
    page.select_option("select[name='day']", "Понедельник")
    page.select_option("select[name='time_slot']", "09:00")
    page.select_option("select[name='color']", "#70a1ff")

    page.locator("#addLessonModal button[type='submit']").click()

    expect(page.locator("text=Автотест Предмет").first).to_be_visible()

    page.locator(".task-card:has-text('Автотест Предмет') button.btn-delete").first().click()
    expect(page.locator("text=Автотест Предмет").first).not_to_be_visible(timeout=10000)


def test_03_add_student(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "alina")
    page.fill("input[name='password']", "teacher123")
    page.click("button[type='submit']")

    page.click("a[href='/students']")
    expect(page).to_have_url(f"{BASE_URL}/students")

    page.locator("button[data-bs-target='#addStudentModal']").click(force=True)
    page.locator("#addStudentModal").wait_for(state="visible")

    page.fill("#addStudentModal input[name='name']", "Иван Тестов")
    page.fill("#addStudentModal input[name='username']", "ivan_test")
    page.fill("#addStudentModal input[name='password']", "student123")
    page.fill("#addStudentModal input[name='age']", "15")
    page.fill("#addStudentModal input[name='contacts']", "+77001234567")

    page.locator("#addStudentModal button[type='submit']").click()
    expect(page.locator("td.fw-bold", has_text="Иван Тестов")).to_be_visible()


def test_04_add_and_delete_grade(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "alina")
    page.fill("input[name='password']", "teacher123")
    page.click("button[type='submit']")

    page.click("a[href='/students']")

    row = page.locator("tr:has-text('Иван Тестов')")
    row.locator("button:has-text('+ Оценка')").click(force=True)

    modal = page.locator(".modal.show").first
    modal.wait_for(state="visible")

    modal.locator("input[name='test_name']").fill("Контрольная работа")
    modal.locator("input[name='score']").fill("9")
    modal.locator("input[name='max_score']").fill("10")
    modal.locator("button[type='submit']").click()

    expect(row.locator("text=9/10")).to_be_visible()

    row.locator(".grade-badge-clickable").click(force=True)
    history_modal = page.locator(".modal.show").last
    history_modal.wait_for(state="visible")

    delete_btn = history_modal.locator("form[action*='/students/grades/delete/'] button")
    if delete_btn.count() > 0:
        delete_btn.first().click()

    close_btn = history_modal.locator("button.btn-close, button[data-bs-dismiss='modal']")
    if close_btn.count() > 0:
        close_btn.first().click()


def test_05_student_login_and_view_grades(page: Page):
    page.goto(f"{BASE_URL}/login")
    page.fill("input[name='username']", "ivan_test")
    page.fill("input[name='password']", "student123")
    page.click("button[type='submit']")

    page.goto(f"{BASE_URL}/my")
    expect(page).to_have_url(f"{BASE_URL}/my")
    expect(page.locator("text=Успеваемость: Иван Тестов")).to_be_visible()

    page.goto(f"{BASE_URL}/schedule")
    expect(page).to_have_url(f"{BASE_URL}/schedule")