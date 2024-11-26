class MissEnvException(Exception):
    """Кастомное исключение для ошибок отсутствия переменных окружения."""

    pass


class ApiTelegramError(Exception):
    """Кастомное исключение для ошибок API."""

    pass


class ApiPracticumError(Exception):
    """Кастомное исключение для ошибок API."""

    pass
