import logging
import os
import time
from typing import Dict, List

from dotenv import load_dotenv
import requests
from telebot import TeleBot

from exceptions import MissEnvException, ApiTelegramError, ApiPracticumError


logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv("YA_TOKEN")
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

RETRY_PERIOD = 600
ENDPOINT = "https://practicum.yandex.ru/api/user_api/homework_statuses/"
HEADERS = {"Authorization": f"OAuth {PRACTICUM_TOKEN}"}

HOMEWORK_VERDICTS = {
    "approved": "Работа проверена: ревьюеру всё понравилось. Ура!",
    "reviewing": "Работа взята на проверку ревьюером.",
    "rejected": "Работа проверена: у ревьюера есть замечания.",
}


def check_tokens():
    """Проверка существования обязательных переменных окружения."""
    missing_vars = []
    if not PRACTICUM_TOKEN:
        missing_vars.append("PRACTICUM_TOKEN")
    if not TELEGRAM_TOKEN:
        missing_vars.append("TELEGRAM_TOKEN")
    if not TELEGRAM_CHAT_ID:
        missing_vars.append("TELEGRAM_CHAT_ID")
    if missing_vars:
        error_msg = ("отсутствуют обязательные переменные окружения: "
                     f"{', '.join(missing_vars)}")
        logging.critical(error_msg)
        raise MissEnvException(error_msg)


def send_message(bot: TeleBot, message: str):
    """Отправка сообщения пользователю Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug("сообщение отправлено пользователю")
    except Exception as e:
        raise ApiTelegramError(f"сбой при отправке сообщения: {e}")


def get_api_answer(from_date: int) -> Dict:
    """Получение ответа от API Практикума."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={"from_date": from_date}
        )
    except requests.RequestException as e:
        raise ApiPracticumError("ошибка при запросе к API Практикума") from e
    if response.status_code != 200:
        raise ApiPracticumError("получен некорректный статус ответа: "
                                f"{response.status_code}")
    return response.json()


def check_response(response: Dict) -> List[Dict]:
    """Проверка корректности ответа от API."""
    if not isinstance(response, dict):
        raise TypeError('Ответ от сервера содержит неверный тип данных - '
                        f'{type(response)}')
    if "homeworks" not in response:
        raise KeyError('В ответе от сервера отсутствует ключ "homeworks"')
    homeworks = response.get("homeworks")
    if not isinstance(homeworks, list):
        raise TypeError('Ключ "homeworks" содержит неверный тип данных - '
                        f'{type(homeworks)}')
    if not homeworks:
        logging.debug("Статус домашней работы не изменился")
    return homeworks


def parse_status(homework: Dict) -> str:
    """Извлечение статуса домашней работы."""
    homework_name = homework.get("homework_name")
    status = homework.get("status")
    if not homework_name or not status:
        raise KeyError("Отсутствуют необходимые поля в ответе сервера")
    verdict = HOMEWORK_VERDICTS.get(status)
    if not verdict:
        raise KeyError(f"Неизвестный статус домашки: {status}")
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    # Проверка наличия обязательных переменных окружения
    check_tokens()
    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    last_checked = int(time.time()) - 3 * 7 * 24 * 60 * 60  # 3 недели назад
    old_error_message = ""

    while True:
        try:
            response = get_api_answer(last_checked)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                last_checked = response.get("current_date", last_checked)
        except ApiTelegramError as error:
            logging.error(error)
        except Exception as error:
            error_message = f"Сбой в работе программы: {error}"
            logging.error(error_message)
            if error_message != old_error_message:
                send_message(bot, error_message)
            old_error_message = error_message
        time.sleep(RETRY_PERIOD)


if __name__ == "__main__":
    main()
