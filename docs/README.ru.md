# RequestBeam Python SDK

[English](../README.md) | [Deutsch](README.de.md) | [Türkçe](README.tr.md) | [Italiano](README.it.md) | [Español](README.es.md) | [Français](README.fr.md) | [Português](README.pt-BR.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md) | [繁體中文](README.zh-TW.md) | [Русский](README.ru.md)

Синхронный и асинхронный Python-клиент для API RequestBeam: текст, изображения, видео, Similarweb и Twitter. Сохраняет исходные ответы и предоставляет ограниченный опрос заданий, события SSE, типизированные ошибки и локальные сообщения на всех 12 публичных языках проекта.

## Установка

Установите из этого репозитория, используя Python 3.10 или новее. Эта версия не опубликована в PyPI; одноименный пакет там не обязательно является этим SDK.

```bash
git clone https://github.com/RequestBeamDev/python_sdk.git
cd python_sdk
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
```

## Аутентификация и язык

Храните ключ API в локальном или серверном окружении. Корень API по умолчанию: `https://api.requestbeam.com`, без добавления `/v1`. `locale` меняет только собственные ошибки SDK, не переводя запросы, поля API, ID моделей и исходные сообщения сервера. Коды: `en`, `de`, `tr`, `it`, `es`, `fr`, `pt-BR` / `pt`, `ja`, `ko`, `zh-CN` / `cn` / `zh`, `zh-TW` / `tw`, `ru`. Регистр и подчеркивания нормализуются. Неподдерживаемый язык вызывает `ValueError`.

Пользовательский `base_url` должен быть HTTPS-источником без учетных данных, пути, строки запроса и фрагмента. ID заданий и пользователей Twitter должны быть непустыми строками из цифр ASCII.

```bash
export REQUESTBEAM_API_KEY="YOUR_API_KEY"
export REQUESTBEAM_TEXT_MODEL="YOUR_TEXT_MODEL_ID"
```

## Текст и асинхронные вызовы

Посмотрите текущий каталог через `list_models()` и задайте подходящий ID в `REQUESTBEAM_TEXT_MODEL`. Наличие в каталоге не гарантирует доступность поставщика сейчас. Ответы являются обычными словарями. Контекстные менеджеры закрывают соединения SDK; переданные HTTP-клиенты остаются под управлением вызывающего кода.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="ru") as client:
    models = client.list_models()
    result = client.chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    )
    print(result)
```

```python
import asyncio
import os
from requestbeam import AsyncRequestBeam

async def main():
    async with AsyncRequestBeam(locale="ru") as client:
        result = await client.chat_completions(
            model=os.environ["REQUESTBEAM_TEXT_MODEL"],
            messages=[{"role": "user", "content": "Hello"}],
        )
        print(result)

asyncio.run(main())
```

## Потоковые ответы

Используйте контекстный менеджер потока даже при досрочном прекращении чтения. Каждый `SSEEvent` содержит `event`, `data`, `id` и `json()`. Данные зависят от протокола; не каждое событие содержит текст. Итератор обрабатывает `[DONE]` внутри. Ошибки потока вызывают исключение SDK.

```python
import os
from requestbeam import RequestBeam

with RequestBeam(locale="ru") as client:
    with client.stream_chat_completions(
        model=os.environ["REQUESTBEAM_TEXT_MODEL"],
        messages=[{"role": "user", "content": "Hello"}],
    ) as events:
        for event in events:
            print(event.event, event.data)
```

## Изображения и видео

Изображения возвращают результат непосредственно через JSON или SSE и не используют Jobs. Отправка видео возвращает строку `data.jobId`. `wait_for_job()` возвращает полный ответ задания после `COMPLETED` и вызывает `JobFailedError` при `FAILED` или `CANCELLED`. Тайм-аут прекращает только локальное ожидание, не отменяя удаленное задание или оплату.

Синхронный опрос задает оставшееся время как тайм-аут каждой HTTP-фазы и проверяет срок между запросами. Он не может принудительно прервать текущий синхронный ответ, поэтому общее время может превысить бюджет. Асинхронный опрос дополнительно ограничивает срок всей текущей заявки. Для потоков используйте `stream_*`; остальные методы отклоняют `stream=True` до отправки.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ru") as client:
    image = client.generate_image(
        model="gpt-image-2", prompt="A red bicycle beside a white wall"
    )
    submission = client.generate_video(
        model="seedance-2.0",
        prompt="A quiet city street at dawn, slow forward camera movement.",
        duration=5,
        resolution="720p",
        aspectRatio="16:9",
        generateAudio=False,
    )
    job = client.wait_for_job(
        submission["data"]["jobId"], timeout=600, poll_interval=5
    )
    print(job["data"]["outputResult"])
```

## Similarweb и Twitter

Similarweb поддерживает 27 разрешенных операций и сохраняет исходные поля ответов. Поддерживаются только мировые данные (`country=999`). Другие допустимые страны преобразуются сервисом в мировые данные, а не данные по стране. При необходимости передавайте `from` и `to` вместе через `**{"from": ..., "to": ...}`; SDK их не изменяет. Пустой результат не означает нулевой трафик.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ru") as client:
    traffic = client.similarweb(
        "websites/visits", keys="example.com", country=999
    )
    print(traffic)
```

Методы Twitter поддерживают поиск по имени, ID и ленту пользователя. Итератор возвращает полные страницы, следует `meta.next_token`, ограничивает число страниц и отклоняет повторные курсоры. Он не объединяет страницы и не гарантирует получение всей ленты. GET-запросы данных могут быть платными; каждая страница является отдельным запросом.

```python
from requestbeam import RequestBeam

with RequestBeam(locale="ru") as client:
    user = client.twitter_user_by_username("TwitterDev")
    user_id = user["data"]["id"]
    for page in client.iter_twitter_user_tweets(
        user_id, max_pages=3, max_results=10
    ):
        print(page)
```

## Ошибки и локальные файлы

`APIError` сохраняет HTTP-статус, код сервиса, исходное сообщение, ID запроса и тело ответа. `TransportError`, `ProtocolError`, `PollingTimeoutError` и `JobFailedError` различают ошибки соединения, протокола, ожидания и задания. Перед публикацией ответов или тел ошибок проверяйте их на конфиденциальные данные. Не помещайте ключи в Git, браузерный код, снимки экрана или логи.

```python
from requestbeam import APIError, RequestBeam

try:
    with RequestBeam(locale="ru") as client:
        client.get_job("123456789012345678")
except APIError as exc:
    print(exc.status_code, exc.code, exc.request_id)
```

Проверяйте структуру ответа перед локальным сохранением. SDK не загружает удаленные файлы автоматически. URL результатов могут истечь; своевременно скачивайте доверенные файлы отдельным HTTP-клиентом без аутентификации, чтобы не отправлять ключ RequestBeam на файловый сервер.

```python
import json
from pathlib import Path

# result: a response obtained from one of the calls above.
Path("result.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
)
```

## Проверка и ограничения

Тесты используют имитированные транспорты и не обращаются к платным API. На 2026-10-29 платная генерация в реальном сервисе, развертывание и публикация в PyPI не выполнялись. Никакие запросы не повторяются автоматически, включая платные GET и отправку генерации. Неизвестные параметры и структуры ответов не нормализуются скрытно. Перед запуском примеров проверьте ограничения модели в документации RequestBeam.

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m build
```

Сигнатуры и различия протоколов: [справочник API](api-reference.md). Объем и границы проверки: [проектные решения](design.md).

[RequestBeam](https://requestbeam.com/ru) · [API](https://requestbeam.com/ru/docs/api-reference/models)
