# CooTalk Transcriptor

Сервис использует контракт из `app/generated/`. Метод `AddTranscriptionTask`
принимает `taskId` и `storageKey` и сразу возвращает `Accepted`. После фоновой
обработки сервис вызывает метод MServer `ReturnTranscriptionResult`; адрес MServer
задаётся переменной `RESULT_RECEIVER_TARGET` (например, `localhost:50052`).

Успешный результат содержит текст, имя модели, длительность обработки, длительность
аудио и real-time factor. Ошибка возвращается в поле `failure` того же результата.

Сервис принимает по gRPC **ключ аудиофайла**, скачивает объект из S3, преобразует
его через FFmpeg в WAV и распознаёт речь моделью GigaAM-v3. Клиент не передаёт
само аудио: файл должен уже находиться в настроенном S3 bucket.

## Что находится в проекте

- `app/main.py` — gRPC-сервер.
- `app/storage/storage.py` — загрузка аудио из S3 и подготовка WAV.
- `app/model/GigaAM-v3/` — код, токенизатор и локальные веса модели.
- `app/proto/transcription.proto` и `app/generated/` — контракт gRPC и Python-код.
- `client.py` — отправляет задачу и печатает её идентификатор.

Вес модели `app/model/GigaAM-v3/pytorch_model.bin` хранится через Git LFS.
Перед первым коммитом выполните `git lfs install`.

## Запуск сервера в Docker

Понадобятся Docker Engine или Docker Desktop с Compose и доступный S3-сервис.
В `app/.env` укажите значения по образцу `app/template.env`:

```dotenv
BUCKET=имя-bucket
ACCESS_KEY=ключ-доступа
SECRET_KEY=секретный-ключ
HF_TOKEN=токен-hugging-face
REGION=
S3_PREFIX=
RESULT_RECEIVER_TARGET=localhost:50052
RESULT_RECEIVER_TIMEOUT_SECONDS=10
```

`HF_TOKEN` используется Pyannote для сегментации аудио. При первом запросе
модель сегментации может загружаться с Hugging Face. Не публикуйте `app/.env`:
он монтируется в контейнер при запуске и не включается в образ.

Compose задаёт адрес S3 через `S3_ENDPOINT`; если переменная не указана,
используется `https://s3.cootalk.ru/`. Значение `ENDPOINT` из `app/.env` в Docker
перекрывается этой настройкой. Чтобы использовать другой адрес, задайте его
перед запуском, например в PowerShell:

```powershell
$env:S3_ENDPOINT = "https://адрес-вашего-s3/"
docker-compose -f compose.yaml build
docker-compose -f compose.yaml up -d --no-build
```

В Docker адрес получателя результатов по умолчанию —
`host.docker.internal:50052`. Его можно изменить через переменную окружения
`RESULT_RECEIVER_TARGET`.

Если порт 50051 на компьютере занят, перед `up` задайте
`$env:GRPC_HOST_PORT = "50052"`. Порт внутри контейнера остаётся 50051.

Посмотреть состояние и логи:

```powershell
docker-compose -f compose.yaml ps
docker-compose -f compose.yaml logs -f transcriptor
```

После изменения ключей в `app/.env` выполните
`docker-compose -f compose.yaml restart transcriptor`. После изменения
`S3_ENDPOINT` или `GRPC_HOST_PORT` пересоздайте контейнер командой
`docker-compose -f compose.yaml up -d --force-recreate --no-build` в той же
оболочке с нужными значениями переменных.

Остановить сервер: `docker-compose -f compose.yaml down`. Кэш Hugging Face
остаётся в отдельном томе. Не используйте `down -v`, если хотите сохранить кэш.

## Запуск клиента

На компьютере клиента нужны Python, `grpcio`, `protobuf`, файл `client.py` и
каталог `app/generated/`. Из корня проекта:

```powershell
python -m pip install grpcio==1.84.0 protobuf==7.36.2
python client.py folder/recording.wav --task-id task-123
```

По умолчанию клиент подключается к `localhost:50051`. Для другого компьютера
или порта укажите адрес сервера:

```powershell
python client.py folder/recording.wav --server 192.168.1.10:50052
```

`folder/recording.wav` здесь — ключ объекта в bucket. Если задан `S3_PREFIX`,
сервер добавляет его перед переданным ключом. Загрузка файла в S3 выполняется
отдельно, до вызова клиента. Если `--task-id` не указан, клиент создаёт UUID.

## Проверка и ошибки

`UNAVAILABLE` при добавлении задачи означает, что клиент не может подключиться к
gRPC-порту. Ошибки обработки (`NOT_FOUND`, `INVALID_ARGUMENT`, `INTERNAL`)
передаются MServer через `TranscriptionResult.failure`. Ошибки доставки результата
также записываются в лог контейнера.

`requirements.txt` и `Dockerfile` фиксируют зависимости сервера для CPU.
Собранный образ содержит одну копию весов GigaAM-v3; несколько контейнеров на
одном Docker-хосте используют общие слои образа, но каждый загружает модель
в собственную оперативную память.
