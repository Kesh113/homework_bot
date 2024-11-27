from http import HTTPStatus
import logging
import os
import sys
import time
from typing import Dict, List

from dotenv import load_dotenv
import requests
from telebot import TeleBot

from exceptions import ApiTelegramError


load_dotenv()

PRACTICUM_TOKEN = os.getenv('YA_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TG_CHAT_ID')

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
    missing_vars = [name for name in [
        'PRACTICUM_TOKEN',
        'TELEGRAM_TOKEN',
        'TELEGRAM_CHAT_ID'
    ] if not globals()[name]]
    if missing_vars:
        error_massage = (
            'отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_vars)}'
        )
        logging.critical(error_massage)
        raise EnvironmentError(error_massage)


def send_message(bot: TeleBot, message: str):
    """Отправка сообщения пользователю Telegram."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'сообщение "{message}" отправлено пользователю')
    except Exception as e:
        raise ApiTelegramError(f'сбой при отправке сообщения "{message}": {e}')


def get_api_answer(from_date: int) -> Dict:
    """Получение ответа от API Практикума."""
    params = {'from_date': from_date}
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
        if response.status_code != HTTPStatus.OK:
            raise requests.HTTPError(
                f'некорректный статус ответа: {response.status_code}'
            )
    except requests.RequestException as e:
        raise RuntimeError(
            f'ошибка при запросе к API Практикума: {e}. '
            f'Параметры запроса: url={ENDPOINT}, '
            f'headers={HEADERS}, params={params}'
        ) from e
    try:
        data = response.json()
    except ValueError as e:
        raise RuntimeError(
            f'ошибка декодирования JSON из ответа: {e}. '
            f'текст ответа: {response.text}. '
            f'Параметры запроса: url={ENDPOINT}, '
            f'headers={HEADERS}, params={params}'
        ) from e
    if 'code' in data or 'error' in data:
        error_detail = data.get('code') or data.get('error')
        raise RuntimeError(
            f'API Практикума вернул ошибку: {error_detail}. '
            f'Параметры запроса: url={ENDPOINT}, '
            f'headers={HEADERS}, params={params}'
        )
    return data


def check_response(response: Dict) -> List[Dict]:
    """Проверка корректности ответа от API."""
    if not isinstance(response, dict):
        raise TypeError(
            'Ответ от сервера содержит неверный тип данных - '
            f'{type(response)}'
        )
    if 'homeworks' not in response:
        raise KeyError('В ответе от сервера отсутствует ключ "homeworks"')
    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(
            'Ключ "homeworks" содержит неверный тип данных - '
            f'{type(homeworks)}'
        )
    return homeworks


def parse_status(homework: Dict) -> str:
    """Извлечение статуса домашней работы."""
    if 'status' not in homework:
        raise KeyError('Отсутствует поле "status" в ответе сервера')
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует поле "homework_name" в ответе сервера')
    name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус домашки: {status}')
    return MESSAGE.format(name, HOMEWORK_VERDICTS[status])


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
                logging.debug('Статус домашней работы не изменился')
        except ApiTelegramError as error:
            logging.error(error, exc_info=True)
        except Exception as error:
            error_message = f'Сбой в работе программы: {error}'
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

    # from unittest import TestCase, mock, main as uni_main
    # ReqEx = requests.RequestException
    # JSON_rejection = {'error': 'testing'}
    # JSON_unexpected = {'homeworks': [{'homework_name': 'test',
    #                                   'status': 'test'}]}
    # JSON_invalid = {'homeworks': 1}

    # class TestReq1(TestCase):
    #     @mock.patch('requests.get')
    #     def test_raised(self, rq_get):
    #         rq_get.side_effect = mock.Mock(
    #             side_effect=ReqEx('testing'))
    #         main()

    # class TestReq2(TestCase):
    #     @mock.patch('requests.get')
    #     def test_error(self, rq_get):
    #         resp = mock.Mock()
    #         resp.json = mock.Mock(
    #             return_value=JSON_rejection)
    #         resp.status_code = 200
    #         rq_get.return_value = resp
    #         main()

    # class TestReq3(TestCase):
    #     @mock.patch('requests.get')
    #     def test_error(self, rq_get):
    #         resp = mock.Mock()
    #         resp.json = mock.Mock(
    #             return_value=JSON_unexpected)
    #         resp.status_code = 200
    #         rq_get.return_value = resp
    #         main()

    # class TestReq4(TestCase):
    #     @mock.patch('requests.get')
    #     def test_error(self, rq_get):
    #         resp = mock.Mock()
    #         resp.json = mock.Mock(
    #             return_value=JSON_invalid)
    #         resp.status_code = 200
    #         rq_get.return_value = resp
    #         main()

    # class TestReq5(TestCase):
    #     @mock.patch('requests.get')
    #     def test_error(self, rq_get):
    #         resp = mock.Mock()
    #         resp.status_code = 333
    #         rq_get.return_value = resp
    #         main()
    # uni_main()
    
