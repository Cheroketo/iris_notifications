# HTTP-сервис уведомлений Iris

Практическая работа №11 по дисциплине «Разработка и интеграция».

## Запуск

Требуется Python 3.12. Из корня репозитория:

```bash
python -m pip install -r requirements.txt
python -m uvicorn notification_service.app.main:app --port 8001
```

OpenAPI доступна по адресу http://127.0.0.1:8001/docs.

`POST /notifications` принимает UUID `message_id`, `text` и необязательный `recipient`. Первый запрос возвращает `201 created` и поле `filename`. Идентичный повтор возвращает `200 duplicate` с тем же именем. Изменение текста или получателя с тем же идентификатором даёт `409 Conflict`.

В каталоге `var` хранятся `processed_ids.sqlite3` и `messages/<UUID>.txt`. Каталог можно переопределить переменной `NOTIFICATIONS_DATA_DIR`. SQLite сохраняет состояние между перезапусками. Каждый файл записывается в UTF-8.

Сервис предсказаний — [Cheroketo/new_repo](https://github.com/Cheroketo/new_repo). Его HTTP-клиент использует `NOTIFICATIONS_URL` с адресом сервиса по умолчанию `http://127.0.0.1:8001`.

## Проверка

```bash
python -m pytest -v
```
