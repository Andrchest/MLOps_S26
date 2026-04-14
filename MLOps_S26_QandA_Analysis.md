# MLOps_S26: Q&A Analysis Report

This document contains the specific architectural and implementation questions and their corresponding answers based on the current state of the `MLOps_S26` repository.

---

**1. Как сервисы общаются между собой? (REST API, gRPC, или они просто читают одну и ту же базу данных?)**
**Ответ:** Сервисы взаимодействуют через:
- **Общую базу данных PostgreSQL**: Используется как основной механизм передачи состояний задач (таблицы `jobs`, `trained_models`) и логирования (`prediction_logs`).
- **REST API**: `orchestrator` предоставляет API для управления заданиями, а `inference-service` предоставляет API для предсказаний.
- **Shared Infrastructure**: Все сервисы используют общие инстансы `PostgreSQL`, `MinIO` и `MLflow`.

**2. Как один сервис узнает адрес другого? (Hardcoded IP, Docker service names, или что-то другое?)**
**Ответ:** Сервисы используют **Docker service names** (например, `postgres`, `minio`, `mlflow`), определенные в `docker-compose.yml`. Это позволяет им находить друг друга внутри Docker-сети без использования жестко заданных IP-адресов.

**3. Можете описать/нарисовать, как данные проходят путь от "пользователь отправил запрос на обучение" до "модель появилась в MinIO"?**
**Ответ:** **NO IMPLEMENTED**. На текущий момент автоматизированный конвейер не реализован. Предполагаемый путь: `User` $\to$ `orchestrator` (`POST /train`) $\to$ запись в БД `jobs` (status='pending') $\to$ `training-worker` (polling) $\to$ обучение $\to$ `training-worker` (upload) $\to$ `MinIO` $\to$ запись в БД `trained_models`.

**4. Как реализована очередь задач?**
**Ответ:** Очередь реализована через **polling (опрос) таблицы `jobs` в PostgreSQL**. `orchestrator` вставляет записи со статусом `pending`, а `training-worker` должен их забирать.

**5. Какие именно статусы есть у задачи (Pending, Running, Success, Failed, Retrying)? Что именно триггерит переход из одного в другой?**
**Ответ:** В базе данных (таблица `jobs`) по умолчанию установлен статус `'pending'`. Остальные статусы (`Running`, `Success`, `Failed`, `Retrying`) **NOT IMPLEMENTED** в текущей логике воркера.

**6. Какие именно поля в таблице jobs или models являются ключевыми? Есть ли там JSONB для метаданных?**
**Ответ:** Да, используются поля JSONB:
- **`jobs`**: `job_id` (PK), `dataset_name`, `dataset_id`, `status`.
- **`trained_models`**: `job_id` (FK), `model_name`, `model_version`, `model_path`, **`metrics` (JSONB)**, **`parameters` (JSONB)**.
- **`prediction_logs`**: **`input_data` (JSONB)**, **`prediction` (JSONB)**.

**7. Как именно запускается код обучения? Это отдельный Python-процесс через subprocess.run(), или это просто вызов функции внутри воркера?**
**Ответ:** **NO IMPLEMENTED**. В текущей версии `training-worker/app.py` отсутствует механизм запуска процесса обучения.

**8. Как модель попадает из скрипта обучения в MinIO? Сначала в локальную папку, потом в MinIO? Как мы гарантируем, что файл не "битый"?**
**Ответ:** Реализовано через `services/training-worker/minio_client.py`: модель сериализуется в буфер `io.BytesIO` через `joblib.dump` и напрямую загружается в MinIO через `minio_client.put_object`. Механизм проверки целостности (checksum) **NOT IMPLEMENTED**.

**9. Как именно мы передаем параметры в MLflow? Мы записываем туда только метрики или еще и гиперпараметры? Как мы связываем run_id из MLflow с нашей записью в PostgreSQL?**
**Ответ:** **NO IMPLEMENTED**. Интеграция с MLflow для записи гиперпараметров и связывания `run_id` с PostgreSQL отсутствует.

**10. Как мы решаем проблему GIL при предсказаниях? Мы используем ProcessPoolExecutor, ThreadPoolExecutor или просто async def?**
**Ответ:** Используется **`ProcessPoolExecutor`** в `services/inference-service/app.py`. Предсказания выполняются в отдельных процессах через `loop.run_in_executor`.

**11. Модель загружается в память при старте сервиса или при каждом запросе? Если при запросе, то как реализовано кэширование (LRU cache)? Где именно оно лежит (в памяти процесса или во внешнем Redis)?**
**Ответ:** Модель загружается **при старте воркеров процесса** (через `initializer` в `ProcessPoolExecutor`, файл `services/inference-service/app.py`). Она находится в памяти процесса.

**12. Как входящий JSON превращается в DataFrame для Scikit-Learn? Мы используем какой-то жесткий schema-validator?**
**Ответ:** В `services/inference-service/predictor.py` используется `pd.DataFrame([input_data])`. Валидация структуры данных осуществляется с помощью **Pydantic** (схема `InputData` в `services/inference-service/schemas.py`).

**13. Что произойдет, если воркер крашнется прямо во время обучения? Задача останется в статусе Running навсегда? Как мы это лечим?**
**Ответ:** **NO IMPLEMENTED**. Механизмы отслеживания "зависших" задач и автоматического восстановления при краше воркера отсутствуют.

**14. Есть ли у нас автоматические повторы (retries), если сервис MinIO или БД временно недоступен?**
**Ответ:** **NO IMPLEMENTED**.

**15. Что будет, если пользователь пришлет в API неверные данные (не те колонки, не те типы)? Система упадет или выдаст ошибку?**
**Ответ:** Система выдаст ошибку **`422 Unprocessable Entity`**. Благодаря FastAPI и Pydantic, валидация данных происходит до того, как запрос попадет в бизнес-логику.
