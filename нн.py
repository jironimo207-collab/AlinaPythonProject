import time
import requests

URL = "https://alinapythonproject.onrender.com/students"  # Замените на URL вашего сайта
INTERVAL = 600  # Интервал в секундах (600 сек = 10 минут)

print(f"Запущен пингер для {URL}")

while True:
    try:
        response = requests.get(URL)
        print(f"[{time.strftime('%H:%M:%S')}] Пинг отправлен. Статус: {response.status_code}")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] Ошибка при запросе: {e}")

    time.sleep(INTERVAL)