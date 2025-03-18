# tg_homework_bot

## Описание проекта

Телеграм бот разработанный для проверки статуса домашней работы в Я.Практикум. Реализован запрос статуса домашней работы и автоматическое получение нового статуса при смене.

## Как развернуть проект

1. **Клонируйте репозиторий**:

```bash
git clone git@github.com:Kesh113/homework_bot.git
cd homework_bot
```

2. **Создание и активация виртуального окружения**

```bash
python -m venv venv
source venv/Scripts/activate
```

3. **Установка зависимостей**

```bash
pip install -r requirements.txt
```

4. **Добавьте обязательные переменные окружения**

Вместо значений переменных подставьте свои.

```bash
echo 'PRACTICUM_TOKEN=1234' >> .env
echo 'TELEGRAM_TOKEN=1234' >> .env
echo 'TELEGRAM_CHAT_ID=1234' >> .env
```

5. **Запуск бота**

```bash
python homework.py
```

## Запуск тестов

```bash
pytest
```
