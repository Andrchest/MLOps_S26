# MLOps_S26 Project Architecture Analysis Report

This report provides a detailed analysis of the current implementation within the `MLOps_S26` repository.

---

## 1. Сервисная коммуникация (Service Communication)
**Status:** IMPLEMENTED
**Details:** Сервисы взаимодействуют через:
- **Общую базу данных PostgreSQL**: Используется как основной механизм передачи состояний задач (таблицы `jobs`, `trained_models`) и логирования (`prediction_logs`).
- **REST API**: `orchestrator` предоставляет API для управления заданиями, а `inference-service` предоставляет API для предсказаний.
- **Shared Infrastructure**: Все сервисы используют общие инстансы `PostgreSQL`, `MinIO` и `MLflow`, описанные в `docker-compose.yml`.

## 2. Обнаружение сервисов (Service Discovery)
**Status:** IMPLEMENTED
**Details:** Сервисы используют **Docker service names** (например, `postgres`, `minio`, `mlflow`), определенные в `docker-compose.yml`. Это позволяет им находить друг друга внутри внутренней сети Docker без использования жестко заданных IP-адресов.

## 3. Путь данных: от запроса на обучение до MinIO
**Status:** **NO IMPLEMENTED**
**Details:** На данный момент полный автоматизированный конвейер (pipeline) не реализован. Согласно архитектурному плану, путь должен проходить через `orchestrator` $\to$ `PostgreSQL` $\to$ `training-worker` $\to$ `MinIO`, но логика автоматического перехода между этими этапами отсутствует.

## 4. Очередь задач (Task Queue)
**Status:** IMPLEMENTED
**Details:** Очередь реализована через **polling (опрос) таблицы `jobs` в PostgreSQL**. `orchestrator` вставляет записи, а `training-worker` должен их забирать.

## 5. Статусы задач (Job Statuses)
**Status:** PARTIALLY IMPLEMENTED
**Details:** 
- В базе данных (таблица `jobs`, файл `migrations/tables_for_worker.sql`) по умолчанию установлен статус `'pending'`.
- Статусы `Running`, `Success`, `Failed`, `Retrying` **NOT IMPLEMENTED** в текущей логике воркера.

## 6. Ключевые поля в БД (Database Schema)
**Status:** IMPLEMENTED
**Details:** 
- **Таблица `jobs`**: `job_id` (PK), `dataset_name`, `dataset_id`, `status`.
- **Таблица `trained_models`**: `job_id` (FK), `model_name`, `model_version`, `model_path`, **`metrics` (JSONB)**, **`parameters` (JSONB)**.
- **Таблица `prediction_logs`**: **`input_data` (JSONB)**, **`prediction` (JSONB)**.
*(См. `migrations/tables_for_worker.sql` и `migrations/pred_logs.sql`)*

## 7. Запуск кода обучения (Training Execution)
**Status:** **NO IMPLEMENTED**
**Details:** В текущей версии `training-worker/app.py` отсутствует механизм запуска процесса обучения (ни через `subprocess.run()`, ни через вызов функции внутри воркера).

## 8. Загрузка модели в MinIO (Model Persistence)
**Status:** IMPLEMENTED
**Details:** Реализовано в `services/training-worker/minio_client.py`:
1. Модель сериализуется в буфер `io.BytesIO` через `joblib.dump`.
2. Буфер загружается в MinIO через `minio_client.put_object`.
3. Возвращается путь к объекту в MinIO.

## 9. Интеграция с MLflow (MLflow Integration)
**Status:** **NO IMPLEMENTED**
**Details:** Передача параметров и связывание `run_id` из MLflow с записью в PostgreSQL **NOT IMPLEMENTED**.

## 10. Решение проблемы GIL (Concurrency)
**Status:** IMPLEMENTED
**Details:** В `services/inference-service/app.py` используется **`ProcessPoolExecutor`**. Предсказания выполняются в отдельных процессах, что позволяет обходить ограничения GIL.

## 11. Загрузка модели в память (Model Loading)
**Status:** IMPLEMENTED
**Details:** Модель загружается **при старте воркеров процесса** (через `initializer` в `ProcessPoolExecutor`, файл `services/inference-service/app.py`). Это обеспечивает высокую скорость ответов, так как модель уже находится в памяти процесса.

## 12. Преобразование JSON в DataFrame (Data Processing)
**Status:** IMPLEMENTED
**Details:** В `services/inference-service/predictor.py` используется `pd.DataFrame([input_data])`. Валидация структуры данных происходит на уровне Pydantic-схем (`services/inference-service/schemas.py`).

## 13. Обработка краша воркера (Worker Failure Recovery)
**Status:** **NO IMPLEMENTED**
**Details:** Механизмы обнаружения зависших задач или автоматического перезапуска при краше воркера **NOT IMPLEMENTED**.

## 14. Автоматические повторы (Retries)
**Status:** **NO IMPLEMENTED**
**Details:** Логика автоматических повторов (retries) при недоступности БД или MinIO **NOT IMPLEMENTED**.

## 15. Обработка неверных данных (Input Validation)
**Status:** IMPLEMENTED
**Details:** Благодаря использованию **FastAPI и Pydantic**, при отправке неверных типов данных или отсутствующих колонок, система возвращает ошибку **`422 Unprocessable Entity`** до начала выполнения бизнес-логики.
