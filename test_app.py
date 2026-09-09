
import pytest
from selenium import webdriver
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
import time

BASE_URL = "http://127.0.0.1:8001"


@pytest.fixture
def driver():
    options = webdriver.FirefoxOptions()
    # options.add_argument("--headless")

    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    driver.implicitly_wait(5)
    yield driver
    driver.quit()


def test_full_lumi_app_workflow(driver):
    wait = WebDriverWait(driver, 10)
    unique_suffix = str(int(time.time()))

    # 1. Авторизация преподавателя
    driver.get(f"{BASE_URL}/login")
    driver.find_element(By.NAME, "username").send_keys("alina")
    driver.find_element(By.NAME, "password").send_keys("teacher123")
    driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
    wait.until(EC.url_contains("/schedule"))

    # ==========================================
    # 2. УРОКИ: Создание -> Удаление
    # ==========================================
    # Создание урока
    driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#addLessonModal']").click()
    title_input = wait.until(EC.visibility_of_element_located((By.NAME, "title")))
    lesson_title = f"Урок {unique_suffix}"
    title_input.send_keys(lesson_title)
    Select(driver.find_element(By.NAME, "day")).select_by_visible_text("Понедельник")
    Select(driver.find_element(By.NAME, "time_slot")).select_by_visible_text("10:00")
    driver.find_element(By.CSS_SELECTOR, "#addLessonModal button[type='submit']").click()
    time.sleep(1)
    assert lesson_title in driver.page_source

    # Удаление урока
    delete_buttons = driver.find_elements(By.CSS_SELECTOR,
                                          ".schedule-cell button.btn-danger, .schedule-cell .btn-close, .card button.btn-danger, div[style*='background'] button, .badge.bg-danger + button, .badge.bg-danger")
    if not delete_buttons:
        # Универсальный поиск маленького крестика или кнопки удаления внутри блока урока
        delete_buttons = driver.find_elements(By.XPATH,
                                              "//div[contains(@class, 'bg-')]//button[contains(@class, 'btn-close') or contains(@class, 'danger')] | //div[contains(text(), 'Урок')]//button")

    if delete_buttons:
        # Берем видимую кнопку удаления
        for btn in reversed(delete_buttons):
            if btn.is_displayed():
                btn.click()
                break

        time.sleep(0.5)
        try:
            driver.switch_to.alert.accept()  # Подтверждаем системный JS диалог (ОК)
        except Exception:
            pass
        time.sleep(1)
        assert lesson_title not in driver.page_source
    # ==========================================
    # 3. УЧЕНИКИ: Создание -> Редактирование -> Удаление
    # ==========================================
    driver.get(f"{BASE_URL}/students")
    student_username = f"student_{unique_suffix}"
    student_name = f"Ученик {unique_suffix}"

    # Создание ученика
    driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#addStudentModal']").click()
    time.sleep(0.5)
    wait.until(EC.visibility_of_element_located((By.NAME, "name"))).send_keys(student_name)
    driver.find_element(By.NAME, "username").send_keys(student_username)
    driver.find_element(By.NAME, "password").send_keys("studentpass123")
    driver.find_element(By.NAME, "age").send_keys("15")
    driver.find_element(By.NAME, "contacts").send_keys("+77771234567")
    driver.find_element(By.CSS_SELECTOR, "#addStudentModal button[type='submit']").click()
    time.sleep(1)
    assert student_name in driver.page_source

    # Редактирование ученика
    edit_student_btns = driver.find_elements(By.CSS_SELECTOR,
                                             "a.btn-warning, a.btn-outline-warning, button.btn-warning, a[href*='edit']")
    if edit_student_btns:
        edit_student_btns[-1].click()
        time.sleep(0.5)
        updated_student_name = f"Измененный Ученик {unique_suffix}"
        name_edit_input = wait.until(EC.visibility_of_element_located((By.NAME, "name")))
        name_edit_input.clear()
        name_edit_input.send_keys(updated_student_name)
        driver.find_element(By.CSS_SELECTOR, "form button[type='submit'], .modal.show button[type='submit']").click()
        time.sleep(1)
        assert updated_student_name in driver.page_source
        student_name = updated_student_name

    # Удаление ученика
    delete_student_btns = driver.find_elements(By.CSS_SELECTOR,
                                               "button.btn-danger, a.btn-danger, form[action*='delete'] button")
    if delete_student_btns:
        delete_student_btns[-1].click()
        time.sleep(0.5)
        try:
            driver.switch_to.alert.accept()
        except Exception:
            pass
        time.sleep(1)
        assert student_name not in driver.page_source

    # ==========================================
    # 4. ГРУППЫ: Создание -> Редактирование -> Удаление
    # ==========================================
    driver.get(f"{BASE_URL}/groups")
    group_name = f"Group {unique_suffix}"

    # Создание группы
    driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#addGroupModal']").click()
    time.sleep(0.5)
    wait.until(EC.visibility_of_element_located((By.NAME, "name"))).send_keys(group_name)
    driver.find_element(By.NAME, "description").send_keys("Вт, Чт 16:00")
    driver.find_element(By.CSS_SELECTOR, "#addGroupModal button[type='submit']").click()
    time.sleep(1)
    assert group_name in driver.page_source

    # Редактирование группы
    edit_group_btns = driver.find_elements(By.CSS_SELECTOR,
                                           "a.btn-warning, a.btn-outline-warning, button.btn-warning, a[href*='edit']")
    if edit_group_btns:
        edit_group_btns[-1].click()
        time.sleep(0.5)
        updated_group_name = f"Pro Group {unique_suffix}"
        group_edit_input = wait.until(EC.visibility_of_element_located((By.NAME, "name")))
        group_edit_input.clear()
        group_edit_input.send_keys(updated_group_name)
        driver.find_element(By.CSS_SELECTOR, "form button[type='submit'], .modal.show button[type='submit']").click()
        time.sleep(1)
        assert updated_group_name in driver.page_source
        group_name = updated_group_name

    # Удаление группы
    delete_group_btns = driver.find_elements(By.CSS_SELECTOR,
                                             "button.btn-danger, a.btn-danger, form[action*='delete'] button")
    if delete_group_btns:
        delete_group_btns[-1].click()
        time.sleep(0.5)
        try:
            driver.switch_to.alert.accept()
        except Exception:
            pass
        time.sleep(1)
        assert group_name not in driver.page_source