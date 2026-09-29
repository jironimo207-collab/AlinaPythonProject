import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Настройка опций (опционально: можно запустить с уже открытым профилем,
# чтобы не вводить логин заново, либо авторизоваться вручную в открытом окне)
options = Options()
# Если хотите использовать свой профиль Firefox (путь к профилю нужно указать ваш):
# options.profile = "/home/имя_пользователя/.mozilla/firefox/ваш_профиль.default-release"

driver = webdriver.Firefox(options=options)
wait = WebDriverWait(driver, 10)

try:
    # 1. Открываем Gemini
    driver.get("https://gemini.google.com/")
    print("Войдите в аккаунт, если потребуется. У вас есть 20 секунд...")
    time.sleep(20)  # Время на ручную авторизацию (или загрузку)

    # 2. Находим кнопку трех точек у нужного чата
    # (Ищем по арии-метке или структуре меню в боковой панели)
    print("Ищем кнопку меню чата...")

    # Пример XPath для кнопки меню (может потребоваться корректировка под текущую верстку)
    # Обычно у кнопки открытия меню чата есть aria-label вроде "Действия с чатом" или похожий
    menu_button = wait.until(
        EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(@aria-label, 'Действия с чатом') or contains(@aria-label, 'Chat options')]"))
    )
    menu_button.click()
    print("Меню открыто.")

    # 3. Ищем кнопку «Удалить» в появившемся контекстном меню
    print("Ищем кнопку удаления...")
    delete_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//div[@role='menu']//span[text()='Удалить' or text()='Delete']/.."))
    )
    delete_button.click()
    print("Нажата кнопка удаления.")

    # 4. Подтверждение удаления (если во всплывающем окне появляется кнопка подтверждения)
    confirm_button = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//button//span[text()='Удалить' or text()='Delete']/.."))
    )
    confirm_button.click()

    # Верификация: проверяем, что кнопка подтверждения пропала или диалог закрылся
    wait.until(EC.invisibility_of_element(confirm_button))
    print("Чат успешно удален и подтвержден!")

except Exception as e:
    print(f"Произошла ошибка при поиске элементов: {e}")

finally:
    # Закрыть браузер
    time.sleep(3)
    driver.quit()