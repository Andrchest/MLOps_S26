# Инструкция по записи демо — MLOps Platform

## Что записывать

Демо показывает полный жизненный цикл ML-модели в распределённой платформе:
загрузка данных → обучение → деплой → инференс → обнаружение дрейфа → автоматическое переобучение → отказоустойчивость.

---

## Подготовка (за 5 минут до записи)

### 1. Запустить платформу
```bash
cd /home/andreipc/MLOps/MLOps_S26
docker compose up -d
```
Подождите 30 секунд, пока все сервисы поднимутся.

### 2. Проверить, что всё работает
Откройте в браузере:
- **MLflow:** http://localhost:5000 — должна быть страница MLflow
- **Grafana:** http://localhost:3000 (логин/пароль: admin/admin) — дашборды
- **Streamlit:** http://localhost:8501 — Streamlit dashboard
- **MinIO:** http://localhost:9001 (логин/пароль: minio/minio123) — файловый менеджер

### 3. Очистить базу данных для чистого демо
```bash
docker compose exec postgres psql -U mlops -d mlops -c "DELETE FROM prediction_logs; DELETE FROM deployments; DELETE FROM trained_models; DELETE FROM jobs; DELETE FROM datasets; ALTER SEQUENCE jobs_job_id_seq RESTART WITH 1; ALTER SEQUENCE datasets_dataset_id_seq RESTART WITH 1; ALTER SEQUENCE deployments_deployment_id_seq RESTART WITH 1;"
```

### 4. Открыть терминал
Откройте терминал в папке `/home/andreipc/MLOps/MLOps_S26` — это будет основное окно записи.

---

## Ход записи (пошагово)

### ШАГ 0: Вступление (10 секунд)
**Что сказать:**
> "Это MLOps платформа — распределённая система для полного жизненного цикла ML-модели. Сейчас я покажу полный цикл: от загрузки данных до автоматического переобучения и отказоустойчивости."

---

### ШАГ 1: Загрузка данных (20 секунд)
**Команда в терминале:**
```bash
bash scripts/demo.sh data 2>&1
```

**Что показать:**
- Вывод скрипта: `Dataset uploaded: id=1`
- Данные попали в MinIO и PostgreSQL

**Что сказать:**
> "Шаг 1 — загрузка данных. CSV-файл загружается в объектное хранилище MinIO и регистрируется в PostgreSQL. Dataset ID = 1."

---

### ШАГ 2: Обучение модели (30-40 секунд)
**Команда в терминале:**
```bash
bash scripts/demo.sh train 2>&1
```

**Что показать:**
- Создание job: `Training job created: job_id=1`
- Статус: `Training completed successfully!`
- Результат обучения (accuracy, metrics)

**Что сказать:**
> "Шаг 2 — обучение модели. Создаётся job, worker его забирает, скачивает данные из MinIO, запускает ML-пайплайн. Результаты логируются в MLflow, модель сохраняется в MinIO."

---

### ШАГ 3: Деплой модели (15 секунд)
**Команда в терминале:**
```bash
bash scripts/demo.sh deploy 2>&1
```

**Что показать:**
- Ответ: `{"deployment_id": 1, "status": "active", ...}`
- Модель доступна для инференса

**Что сказать:**
> "Шаг 3 — деплой. Модель становится активной, доступна для инференса через API."

---

### ШАГ 4: Инференс (20 секунд)
**Команда в терминале:**
```bash
bash scripts/demo.sh infer 2>&1
```

**Что показать:**
- Ответ с предсказанием: `{"prediction": {"label": 1, "score": 0.51}, "latency_ms": 3063}`
- 5 дополнительных предсказаний для сбора метрик

**Что сказать:**
> "Шаг 4 — инференс. Модель предсказывает класс и вероятность. Каждое предсказание логируется с метрикой latency. Сейчас делаем 5 предсказаний для сбора статистики."

---

### ШАГ 5: Обнаружение дрейфа и переобучение (30 секунд)
**Команда в терминале:**
```bash
bash scripts/demo.sh drift 2>&1
```

**Что показать:**
- Предсказание с аномальными данными: `{"age": 999, "monthly_spend": 99999}`
- Ответ: `Drift-triggered retraining jobs found: 2|customer_churn|pending`

**Что сказать:**
> "Шаг 5 — обнаружение дрейфа. Отправляю аномальные данные (возраст 999, доход 999999). Система обнаруживает дрейф и автоматически создаёт job на переобучение. Модель будет переобучена на свежих данных."

**Дополнительно показать (по желанию):**
```bash
docker compose exec postgres psql -U mlops -d mlops -c "SELECT * FROM jobs WHERE status='pending';"
```

---

### ШАГ 6: Отказоустойчивость (30 секунд)
**Команда в терминале:**
```bash
bash scripts/demo.sh fault 2>&1
```

**Что показать:**
- Остановка контейнера: `training-worker container stopped`
- Проверка здоровья: `Inference service is still healthy despite training-worker being down`
- Восстановление: `training-worker is back up and running`
- Финальная таблица: все сервисы в статусе `Up`

**Что сказать:**
> "Шаг 6 — отказоустойчивость. Останавливаю worker, который выполняет обучение. Инференс и оркестратор продолжают работать — они не зависят от worker'а. Через несколько секунд worker автоматически перезапускается и продолжает обработку."

---

### ШАГ 7: Финал — обзор сервисов (20 секунд)
**Команда в терминале:**
```bash
bash scripts/demo.sh all 2>&1 | tail -20
```

**ИЛИ показать в браузере:**
1. **MLflow** (http://localhost:5000) — эксперименты, метрики, артефакты
2. **Grafana** (http://localhost:3000) — дашборды мониторинга
3. **Streamlit** (http://localhost:8501) — операционный дашборд

**Что сказать:**
> "Платформа включает: MLflow для трекинга экспериментов, Grafana для мониторинга в реальном времени, Streamlit для операционного дашборда. Все 10 сервисов работают вместе."

---

## Быстрая шпаргалка — все команды

```bash
cd /home/andreipc/MLOps/MLOps_S26

# Запустить платформу
docker compose up -d

# Очистить БД для нового демо
docker compose exec postgres psql -U mlops -d mlops -c "DELETE FROM prediction_logs; DELETE FROM deployments; DELETE FROM trained_models; DELETE FROM jobs; DELETE FROM datasets; ALTER SEQUENCE jobs_job_id_seq RESTART WITH 1; ALTER SEQUENCE datasets_dataset_id_seq RESTART WITH 1; ALTER SEQUENCE deployments_deployment_id_seq RESTART WITH 1;"

# Полное демо (все шаги)
bash scripts/demo.sh all

# Или по шагам:
bash scripts/demo.sh data
bash scripts/demo.sh train
bash scripts/demo.sh deploy
bash scripts/demo.sh infer
bash scripts/demo.sh drift
bash scripts/demo.sh fault

# Остановить платформу
docker compose down
```

---

## Что делать если что-то пошло не так

### Проблема: "Dataset already exists"
**Решение:** Очистите БД (см. шаг подготовки, пункт 3)

### Проблема: "Training failed"
**Решение:** Проверьте логи worker'а:
```bash
docker compose logs training-worker --tail=30
```
Перезапустите worker:
```bash
docker compose restart training-worker
```

### Проблема: "Not Found" при деплое
**Решение:** Модель ещё не обучена. Сначала выполните шаг train.

### Проблема: сервисы не запускаются
**Решение:** Полная перезагрузка:
```bash
docker compose down -v
docker compose up -d --build
sleep 30
```

---

## Архитектура платформы (для вопросов)

```
┌─────────────────────────────────────────────────────────────┐
│                    MLOps Platform                           │
├─────────────┬─────────────┬─────────────┬─────────────────┤
│ Orchestrator│ Training    │ Inference   │ Monitoring      │
│ :8000       │ Worker      │ Service     │ Dashboards      │
│ Управление  │ :8500       │ :8001       │ Grafana:3000    │
│ job'ами     │ Обучение    │ Инференс    │ Streamlit:8501  │
├─────────────┴─────────────┴─────────────┴─────────────────┤
│              Инфраструктура                                │
│  PostgreSQL:5432  │  MinIO:9000  │  MLflow:5000           │
│  Метаданные       │  Хранилище   │  Эксперименты          │
└─────────────────────────────────────────────────────────────┘
```

### Ключевые возможности:
- **Дрейф данных** — автоматическое обнаружение через статистические тесты
- **Отказоустойчивость** — circuit breakers, retry logic, graceful degradation
- **Планируемое переобучение** — фоновый сервис, настраиваемый интервал
- **Мониторинг** — Prometheus метрики + Grafana дашборды + prediction logs
- **CI/CD** — GitHub Actions с тестами, линтингом, Docker build, Trivy
