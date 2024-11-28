from http import HTTPStatus
import logging
import os
import sys
import time
from typing import Dict, List

from dotenv import load_dotenv
import requests
from telebot import TeleBot

from exceptions import ApiTelegramError, HTTPStatusError


load_dotenv()

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TG_CHAT_ID')
ENV_VARIABLES = [
    'PRACTICUM_TOKEN',
    'TELEGRAM_TOKEN',
    'TELEGRAM_CHAT_ID'
]

ENV_ERROR = 'отсутствуют обязательные переменные окружения: {}'
MESSAGE_HAS_SEND = 'сообщение "{}" отправлено пользователю'
MESSAGE_HAS_NOT_SEND = 'сбой при отправке сообщения "{}": {}'
PRACTICUM_CONNECTION_ERROR = 'ошибка при запросе к API Практикума: {}. {}'
PARAMETERS = 'Параметры запроса: url={}, headers={}, params={}'
INCORRECT_STATUS_CODE = 'некорректный статус ответа: {}'
PRACTICUM_RETURN_ERROR = 'API Практикума вернул ошибку: {}. {}'
INVALID_DATA_TYPE = 'ответ от сервера содержит неверный тип данных - {}'
EMPTY_KEY_HOMEWORKS = 'В ответе от сервера отсутствует ключ "homeworks"'
INVALID_HOMEWORKS_TYPE = 'Ключ "homeworks" содержит неверный тип данных - {}'
EMPTY_STATUS = 'отсутствует поле "status" в ответе сервера'
EMPTY_HOMEWORK_NAME = 'Отсутствует поле "homework_name" в ответе сервера'
UNKNOWN_STATUS = 'неизвестный статус домашки: {}'
STATUS_NOT_CHANGE = 'статус домашней работы не изменился'
MAIN_ERROR = 'Cбой в работе программы: {}'

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.',
}

MESSAGE = 'Изменился статус проверки работы "{}". {}'


def check_tokens():
    """Проверка существования обязательных переменных окружения."""
    missing_vars = [name for name in ENV_VARIABLES if not globals()[name]]
    if missing_vars:
        error_massage = ENV_ERROR.format(missing_vars)
        logging.critical(error_massage)
        raise EnvironmentError(error_massage)


def send_message(bot: TeleBot, message: str):
    """Отправка сообщения пользователю Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(MESSAGE_HAS_SEND.format(message))
    except Exception as error:
        raise ApiTelegramError(
            MESSAGE_HAS_NOT_SEND.format(message, error)) from error


def get_api_answer(from_date: int) -> Dict:
    """Получение ответа от API Практикума."""
    params = {'from_date': from_date}
    params_message = PARAMETERS.format(ENDPOINT, HEADERS, params)
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except requests.RequestException as error:
        raise ConnectionError(
            PRACTICUM_CONNECTION_ERROR.format(error, params_message)
        ) from error
    if response.status_code != HTTPStatus.OK:
        raise HTTPStatusError(
            f'{INCORRECT_STATUS_CODE.format(response.status_code)}'
            f'{params_message}'
        )
    data = response.json()
    if 'code' in data or 'error' in data:
        raise ValueError(PRACTICUM_RETURN_ERROR.format(data, params_message))
    return data


def check_response(response: Dict) -> List[Dict]:
    """Проверка корректности ответа от API."""
    if not isinstance(response, dict):
        raise TypeError(INVALID_DATA_TYPE.format(type(response)))
    if 'homeworks' not in response:
        raise KeyError(EMPTY_KEY_HOMEWORKS)
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(INVALID_HOMEWORKS_TYPE.format(type(homeworks)))
    return homeworks


def parse_status(homework: Dict) -> str:
    """Извлечение статуса домашней работы."""
    if 'status' not in homework:
        raise KeyError(EMPTY_STATUS)
    if 'homework_name' not in homework:
        raise KeyError(EMPTY_HOMEWORK_NAME)
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(UNKNOWN_STATUS.format(status))
    return MESSAGE.format(homework['homework_name'], HOMEWORK_VERDICTS[status])


def main():
    """Основная логика работы бота."""
    # Проверка наличия обязательных переменных окружения
    check_tokens()
    # Создаем объект класса бота
    bot = TeleBot(token=TELEGRAM_TOKEN)
    last_checked = int(time.time())
    old_error_message = ''

    while True:
        try:
            response = get_api_answer(last_checked)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(bot, message)
                last_checked = response.get('current_date', last_checked)
            else:
                logging.debug(STATUS_NOT_CHANGE)
        except ApiTelegramError as error:
            logging.error(error, exc_info=True)
        except Exception as error:
            error_message = MAIN_ERROR.format(error)
            logging.error(error_message)
            if error_message != old_error_message:
                try:
                    send_message(bot, error_message)
                except ApiTelegramError as error:
                    logging.error(error, exc_info=True)
                old_error_message = error_message
        time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format=(
            "%(asctime)s [%(levelname)s] func: "
            "%(funcName)s - line:%(lineno)d - %(message)s"
        ),
        handlers=[
            logging.StreamHandler(stream=sys.stdout),
            logging.FileHandler(
                filename=f"{__file__}.log",
                mode="w",
                encoding="utf-8"
            ),
        ],
    )
    main()
