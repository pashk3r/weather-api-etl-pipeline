# Weather API ETL Pipeline

Учебный пет-проект для ежедневного сбора почасового прогноза погоды в шести областных центрах Беларуси: Минске, Могилёве, Бресте, Гродно, Гомеле и Витебске. Пайплайн получает данные из Open-Meteo, сохраняет исходные JSON ответы в MinIO, очищает их и загружает в PostgreSQL. На основе почасовых данных строится суточная витрина для анализа в Apache Superset. Запусками и проверками качества управляет Apache Airflow.

## Как работает пайплайн

```text
Open-Meteo Forecast API
         │
         ▼
Bronze: MinIO — исходный JSON и метаданные запроса
         │
         ▼
Silver: PostgreSQL — очищенные почасовые данные
         │
         ▼
Gold: PostgreSQL — суточные показатели по городам
         │
         ▼
Superset — SQL-запросы, графики и дашборды
```

Один запуск обрабатывает одну календарную дату. При полном ответе API это 24 наблюдения на город: 144 строки Silver и 6 строк Gold.

DAG `weather_etl_pipeline` запускается ежедневно в **00:00 по Минску**.

| Задача Airflow | Назначение |
|---|---|
| `extract_to_bronze` | Получить данные для каждого города и сохранить ответы в MinIO |
| `validate_bronze` | Проверить наличие шести городов и почасовых данных |
| `load_to_silver` | Нормализовать данные, отфильтровать некорректные записи и дубли, загрузить результат в PostgreSQL |
| `validate_silver` | Проверить наличие городов и допустимые диапазоны показателей |
| `build_gold_mart` | Рассчитать суточные показатели из Silver |
| `validate_gold` | Проверить количество строк и корректность агрегатов |

Silver содержит температуру, влажность, ощущаемую температуру, осадки, дождь, снег, код погоды, скорость и направление ветра. Время хранится как `TIMESTAMPTZ`.

Gold содержит среднюю, минимальную и максимальную температуру, среднюю ощущаемую температуру, сумму осадков, максимальную скорость ветра, количество часов с осадками и число наблюдений.

### Повторные запуски

- **Bronze:** объект хранится в бакете `weather` по ключу `weather-forecast/bronze/year=YYYY/month=MM/day=DD/<city>.json`. Новый запуск за ту же дату перезаписывает JSON города.
- **Silver:** предыдущие наблюдения шести городов за дату удаляются, затем новые вставляются в одной транзакции. При ошибке вставки удаление откатывается. Данные других дат сохраняются.
- **Gold:** строки за дату обновляются через UPSERT по ключу `(date, city_id)`.

У DAG задан `max_active_runs=1`: scheduler выполняет не более одного его запуска одновременно. Задачи имеют три повторные попытки с интервалом две минуты. Silver и Gold обновляются отдельными задачами: при ошибке после загрузки Silver витрина Gold может оставаться прежней до успешного завершения обработки.

## Используемые технологии

- Python 3.12 
- pandas, requests, psycopg, minio 
- MinIO 
- PostgreSQL 17.6 
- Apache Airflow 3.3.2 
- Apache Superset 6.0.0 
- Docker Compose 

## Структура проекта

```text
weather-api-etl-pipeline/
├── dags/
│   └── weather_etl_pipeline.py   # Расписание и последовательность задач
├── src/
│   ├── __init__.py
│   ├── api.py                    # OpenMeteoClient: HTTP-запросы и повторы
│   ├── bronze.py                 # BronzeStorage: сохранение и проверка JSON
│   ├── config.py                 # Settings, City и список городов
│   ├── fields.py                 # Поля API и колонки Silver
│   ├── pipeline.py               # WeatherPipeline: сборка ETL-компонентов
│   ├── transformer.py            # WeatherTransformer: очистка и нормализация
│   └── warehouse.py              # WeatherWarehouse: загрузка, агрегация и проверки
├── sql/
│   └── 01_schemas.sql            # Создание схем Silver/Gold и таблиц в этих схемах 
├── docker/
│   ├── airflow                   # Airflow с зависимостями проекта
│   │   └── Dockerfile
│   └── superset                  # Superset с драйвером PostgreSQL
│       └── Dockerfile
├── .dockerignore                 # Исключения из контекста Docker-сборки
├── .env.example                  # Шаблон переменных окружения
├── .gitignore
├── docker-compose.yaml           # Сервисы, сеть, порты и постоянные тома
├── requirements.txt
└── README.md
```


## Как запустить?


### 1. Скачать проект

```powershell
git clone https://github.com/pashk3r/weather-api-etl-pipeline.git
cd weather-api-etl-pipeline
```

### 2. Настроить переменные окружения

Создайте `.env` из шаблона:

```bash
cp .env.example .env
```

### 3. Запуск контейнеров

```powershell
docker compose up --build -d
```

### 4. Airflow

Чтобы открыть Airflow переходим в браузер по ссылке https://localhost:8080

Airflow доступен без пароля с правами администратора. 

Найди DAG `weather_etl_pipeline` и убедитесь, что он включён.



### 5. Проверить исходные данные в MinIO

Чтобы открыть MinIO: https://localhost:9001

Используй логин и пароль из `.env`:
- логин - `MINIO_ROOT_USER`;
- пароль - `MINIO_ROOT_PASSWORD`.

После успешного запуска в бакете `weather` появятся JSON-файлы:

```text
weather-forecast/bronze/year=YYYY/month=MM/day=DD/<city>.json
```

### 6. Подключить данные к Superset

Superset - http://localhost:8088

При первой установке используются:

```text
Логин: admin
Пароль: admin
```

Выберите **+ → Data → Connect database → PostgreSQL** и заполни форму:

| Поле | Значение |
|---|---|
| Host | `dwh` |
| Port | `5432` |
| Database name | Значение `POSTGRES_DWH_DB` из `.env` |
| Username | Значение `POSTGRES_DWH_USER` |
| Password | Значение `POSTGRES_DWH_PASSWORD` |
| Display Name | `weather_dwh` |
| Additional Parameters | Оставить пустым |
| SSL | Выключить для текущего локального PostgreSQL |

Нажать на **Connect**.

Superset подключается к PostgreSQL внутри Docker-сети по адресу `dwh:5432`. Для подключения из программы на компьютере, например DBeaver, используй `localhost:5433`.

После подключения нажмите **Create dataset** и выбери:

```text
Database: weather_dwh
Schema: gold
Table: daily_weather_summary
```

Для работы с почасовыми данными аналогично добавь:

```text
Database: weather_dwh
Schema: silver
Table: weather_observations
```

Подключение и датасеты сохраняются между перезапусками контейнеров.

### 7. Проверить результат загрузки

В Superset откройте **SQL -> SQL Lab**, выберите `weather_dwh` и выполните:

```sql
SELECT
    date,
    city_name,
    observation_count,
    avg_temperature,
    total_precipitation
FROM gold.daily_weather_summary
ORDER BY date DESC, city_name;
```


### Остановка и повторный запуск

Остановить проект с сохранением данных:

```powershell
docker compose stop
```

Запустить повторно:

```powershell
docker compose up -d
```

Пересобрать после изменения Dockerfile или зависимостей:

```powershell
docker compose up --build -d
```

> Не выполняйте `docker compose down -v`, если хотите сохранить данные. Эта команда удаляет тома с базами PostgreSQL, файлами MinIO и настройками Superset.


## **Автор**

**[pashk3r](https://github.com/pashk3r)**