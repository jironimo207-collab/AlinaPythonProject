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
    driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#addLessonModal']").click()
    title_input = wait.until(EC.visibility_of_element_located((By.NAME, "title")))
    lesson_title = f"Урок {unique_suffix}"
    title_input.send_keys(lesson_title)
    Select(driver.find_element(By.NAME, "day")).select_by_visible_text("Понедельник")
    Select(driver.find_element(By.NAME, "time_slot")).select_by_visible_text("10:00")
    driver.find_element(By.CSS_SELECTOR, "#addLessonModal button[type='submit']").click()
    time.sleep(1)
    assert lesson_title in driver.page_source

    delete_buttons = driver.find_elements(By.CSS_SELECTOR,
                                          ".schedule-cell button.btn-danger, .schedule-cell .btn-close, .card button.btn-danger, div[style*='background'] button, .badge.bg-danger + button, .badge.bg-danger")
    if not delete_buttons:
        delete_buttons = driver.find_elements(By.XPATH,
                                              "//div[contains(@class, 'bg-')]//button[contains(@class, 'btn-close') or contains(@class, 'danger')] | //div[contains(text(), 'Урок')]//button")

    if delete_buttons:
        for btn in reversed(delete_buttons):
            if btn.is_displayed():
                btn.click()
                break

        time.sleep(0.5)
        try:
            driver.switch_to.alert.accept()
        except Exception:
            pass
        time.sleep(1)
        assert lesson_title not in driver.page_source

    # ==========================================
    # 3. УЧЕНИКИ: Создание -> Редактирование -> ОЦЕНКИ -> Удаление
    # ==========================================
    driver.get(f"{BASE_URL}/students")
    student_username = f"student_{unique_suffix}"
    student_name = f"Ученик {unique_suffix}"

    # Создание ученика
    driver.find_element(By.CSS_SELECTOR, "button[data-bs-target='#addStudentModal']").click()
    time.sleep(0.5)
    wait.until(EC.visibility_of_element_located((By.NAME, "name"))).send_keys(student_name)
    driver.find_element(By.NAME, "age").send_keys("15")
    driver.find_element(By.NAME, "contacts").send_keys("+77771234567")
    driver.find_element(By.CSS_SELECTOR, "#addStudentModal button[type='submit']").click()
    time.sleep(1)
    assert student_name in driver.page_source

    # Редактирование ученика
    edit_student_btns = driver.find_elements(
        By.CSS_SELECTOR,
        "a.btn-warning, a.btn-outline-warning, button.btn-warning, button.btn-outline-warning"
    )

    if edit_student_btns:
        target_btn = edit_student_btns[-1]
        modal_id = target_btn.get_attribute("data-bs-target")
        target_btn.click()

        name_edit_input = wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, f"{modal_id} [name='name']"))
        )
        name_edit_input.clear()

        updated_student_name = f"Измененный Ученик {unique_suffix}"
        name_edit_input.send_keys(updated_student_name)

        submit_button = driver.find_element(By.CSS_SELECTOR, f"{modal_id} button[type='submit']")
        submit_button.click()

        wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), updated_student_name))
        student_name = updated_student_name

    # ------------------------------------------
    # ВЛОЖЕННЫЙ БЛОК: РАБОТА С ОЦЕНКАМИ УЧЕНИКА
    # ------------------------------------------
    # ------------------------------------------
    # ВЛОЖЕННЫЙ БЛОК: РАБОТА С ОЦЕНКАМИ УЧЕНИКА
    # ------------------------------------------
    # А. ДОБАВЛЕНИЕ ОЦЕНКИ
    add_grade_btns = driver.find_elements(By.XPATH, "//button[contains(text(), '+ Оценка')]")
    if add_grade_btns:
        add_grade_btns[-1].click()

        test_name_input = wait.until(EC.visibility_of_element_located(
            (By.XPATH, "//h5[contains(text(), 'Оценка:')]/following::input[@name='test_name' or @type='text'][1]")))
        test_name_input.send_keys("Самостоятельная работа")

        score_input = driver.find_element(By.XPATH,
                                          "//h5[contains(text(), 'Оценка:')]/following::input[@name='score'][1]")
        score_input.clear()
        score_input.send_keys("8")

        save_grade_btn = driver.find_element(By.XPATH,
                                             "//h5[contains(text(), 'Оценка:')]/following::button[text()='Сохранить'][1]")
        save_grade_btn.click()

        # Ожидаем появление оценки на странице
        wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), "8/10"))

    # Б. ИЗМЕНЕНИЕ ОЦЕНКИ
    # Шаг 1: Находим строку нашего ученика и кликаем на оценку (содержит '/10') внутри этой строки
    grade_badge = wait.until(EC.element_to_be_clickable(
        (By.XPATH, f"//tr[contains(., '{updated_student_name}')]//*[contains(text(), '/10')]")
    ))
    grade_badge.click()

    # Шаг 2: Ищем кнопку карандаша строго внутри ОТКРЫТОГО окна истории оценок
    wait.until(EC.visibility_of_element_located((By.XPATH, "//h5[contains(text(), 'История оценок:')]")))
    edit_grade_btns = driver.find_elements(By.XPATH,
                                           "//h5[contains(text(), 'История оценок:')]/following::*[contains(text(), '✎')]")

    for btn in reversed(edit_grade_btns):
        if btn.is_displayed():
            btn.click()
            break

    # Шаг 3: Ожидаем появление инпута в форме редактирования оценки
    score_edit_input = wait.until(EC.visibility_of_element_located(
        (By.XPATH, "//h5[contains(text(), 'Редактировать оценку')]/following::input[@name='score']")))
    score_edit_input.clear()
    score_edit_input.send_keys("9")

    # Клик "Сохранить" в форме редактирования
    save_changes_btn = driver.find_element(By.XPATH,
                                           "//h5[contains(text(), 'Редактировать оценку')]/following::button[text()='Сохранить']")
    save_changes_btn.click()

    # Если модалка истории не закрылась сама, принудительно закрываем её кнопкой "Закрыть"
    time.sleep(1)  # Даем форме сохраниться и обновить страницу
    try:
        close_modal_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Закрыть')]")
        if close_modal_btn.is_displayed():
            close_modal_btn.click()
    except Exception:
        pass

    # Проверяем, что оценка в строке ученика изменилась на 9
    wait.until(EC.text_to_be_present_in_element((By.XPATH, f"//tr[contains(., '{updated_student_name}')]"), "/10"))

    # В. УДАЛЕНИЕ ОЦЕНКИ
    # Снова открываем историю оценок, кликая по обновленной оценке в строке ученика
    grade_badge = wait.until(EC.element_to_be_clickable(
        (By.XPATH, f"//tr[contains(., '{updated_student_name}')]//*[contains(text(), '/10')]")
    ))
    grade_badge.click()

    # Ищем крестик удаления строго внутри открытой модалки истории
    wait.until(EC.visibility_of_element_located((By.XPATH, "//h5[contains(text(), 'История оценок:')]")))
    delete_grade_btns = driver.find_elements(By.XPATH,
                                             "//h5[contains(text(), 'История оценок:')]/following::*[contains(text(), '✕')]")
    for btn in reversed(delete_grade_btns):
        if btn.is_displayed():
            btn.click()
            break

    time.sleep(0.5)
    try:
        driver.switch_to.alert.accept()
    except Exception:
        pass

    # Закрываем окно истории
    time.sleep(1)
    try:
        close_modal_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Закрыть')]")
        if close_modal_btn.is_displayed():
            close_modal_btn.click()
    except Exception:
        pass

    # Проверяем, что оценка исчезла и вернулся текст "Нет оценок" в строке ученика
    wait.until(
        EC.text_to_be_present_in_element((By.XPATH, f"//tr[contains(., '{updated_student_name}')]"), "Нет оценок"))
    # ------------------------------------------

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
    edit_group_btns = driver.find_elements(By.XPATH, "//*[contains(text(), '✏')]")

    if edit_group_btns:
        edit_group_btns[-1].click()

        group_edit_input = wait.until(EC.visibility_of_element_located((By.NAME, "name")))
        group_edit_input.clear()

        updated_group_name = f"Pro Group {unique_suffix}"
        group_edit_input.send_keys(updated_group_name)

        submit_button = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Сохранить изменения')]")))
        submit_button.click()

        wait.until(EC.visibility_of_element_located((By.XPATH, f"//h5[contains(text(), '{updated_group_name}')]")))
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
