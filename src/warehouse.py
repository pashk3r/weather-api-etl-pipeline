from datetime import date, datetime, time, timedelta
from typing import Any, Iterable
from zoneinfo import ZoneInfo

import psycopg

from src.config import CITIES
from src.fields import SILVER_COLUMNS


# Класс отвечает за работу с PostgreSQL: загружает почасовые данные в Silver, 
# рассчитывает суточную витрину Gold и проверяет результат
class WeatherWarehouse:
    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    # Метод для загрузки почасовых данных в Silver-хранилище
    def replace_observations(self, records: Iterable[dict[str, Any]], processing_date: date) -> None:
        rows = list(records)
        day_start = datetime.combine(processing_date, time.min, ZoneInfo("Europe/Minsk"))
        day_end = day_start + timedelta(days=1)
        self._validate_observations(rows, day_start, day_end)

        city_ids = [city.id for city in CITIES]
        sql = f"""
            INSERT INTO silver.weather_observations ({", ".join(SILVER_COLUMNS)})
            VALUES ({", ".join("%s" for _ in SILVER_COLUMNS)})
        """
        values = [tuple(row[column] for column in SILVER_COLUMNS) for row in rows]

        with psycopg.connect(self.dsn) as connection, connection.cursor() as cursor:
            cursor.execute(
                """DELETE FROM silver.weather_observations
                   WHERE city_id = ANY(%s)
                     AND observation_time >= %s
                     AND observation_time < %s""",
                (city_ids, day_start, day_end),
            )
            cursor.executemany(sql, values)

    def _validate_observations(self, rows: list[dict[str, Any]], day_start: datetime, day_end: datetime) -> None:
        if not rows:
            raise ValueError("Нет данных для загрузки в Silver")
        
        if {row["city_id"] for row in rows} != {city.id for city in CITIES}:
            raise ValueError("Для загрузки в Silver нужны наблюдения по всем шести городам")

        for row in rows:
            observed_at = row["observation_time"]
        
            if isinstance(observed_at, str):
                observed_at = datetime.fromisoformat(observed_at)
        
            if observed_at.utcoffset() is None or not day_start <= observed_at < day_end:
                raise ValueError("Наблюдения должны быть за указанную дату по Минску")

    # Метод для проверки качества данных в Silver-хранилище
    def validate_silver(self, processing_date: date) -> None:
        sql = """
            SELECT count(*), 
                   count(DISTINCT city_id),
                   count(*) FILTER (WHERE temperature_2m NOT BETWEEN -100 AND 100
                     OR relative_humidity_2m NOT BETWEEN 0 AND 100
                     OR precipitation < 0 OR wind_speed_10m < 0)
            FROM silver.weather_observations
            WHERE (observation_time AT TIME ZONE 'Europe/Minsk')::date = %s
        """
        row_count, city_count, invalid_count = self._fetch_one(sql, processing_date)
        
        if row_count == 0 or city_count != len(CITIES) or invalid_count:
            raise ValueError("Проверка качества данных слоя Silver не пройдена")

    # Метод для построения суточной витрины Gold
    def build_daily_summary(self, processing_date: date) -> None:
        sql = """
            INSERT INTO gold.daily_weather_summary (
                date, 
                city_id, 
                city_name, 
                avg_temperature, 
                min_temperature,
                max_temperature, 
                avg_apparent_temperature, 
                total_precipitation,
                max_wind_speed, 
                precipitation_hours, 
                observation_count
            )
            SELECT (observation_time AT TIME ZONE 'Europe/Minsk')::date,
                   city_id, 
                   max(city_name), 
                   avg(temperature_2m), 
                   min(temperature_2m),
                   max(temperature_2m), 
                   avg(apparent_temperature), 
                   sum(precipitation),
                   max(wind_speed_10m), 
                   count(*) FILTER (WHERE precipitation > 0), 
                   count(*)
            FROM silver.weather_observations
            WHERE (observation_time AT TIME ZONE 'Europe/Minsk')::date = %s
            GROUP BY (observation_time AT TIME ZONE 'Europe/Minsk')::date, city_id
            ON CONFLICT (date, city_id) DO UPDATE SET
                city_name = EXCLUDED.city_name,
                avg_temperature = EXCLUDED.avg_temperature,
                min_temperature = EXCLUDED.min_temperature,
                max_temperature = EXCLUDED.max_temperature,
                avg_apparent_temperature = EXCLUDED.avg_apparent_temperature,
                total_precipitation = EXCLUDED.total_precipitation,
                max_wind_speed = EXCLUDED.max_wind_speed,
                precipitation_hours = EXCLUDED.precipitation_hours,
                observation_count = EXCLUDED.observation_count,
                loaded_at = now()
        """

        with psycopg.connect(self.dsn) as connection, connection.cursor() as cursor:
            cursor.execute(sql, (processing_date,))

    # Метод для проверки качества данных в Gold-хранилище
    def validate_gold(self, processing_date: date) -> None:
        sql = """
            SELECT count(*), 
                    count(*) FILTER (
                        WHERE min_temperature > avg_temperature
                        OR avg_temperature > max_temperature
                        OR observation_count <= 0
                        OR total_precipitation < 0
                        OR max_wind_speed < 0
                    )
            FROM gold.daily_weather_summary
            WHERE date = %s
        """
        row_count, invalid_count = self._fetch_one(sql, processing_date)

        if row_count != len(CITIES) or invalid_count:
            raise ValueError("Проверка качества данных слоя Gold не пройдена")

    # Метод для выполнения SQL-запроса 
    def _fetch_one(self, sql: str, parameter: date) -> tuple:
        with psycopg.connect(self.dsn) as connection, connection.cursor() as cursor:
            cursor.execute(sql, (parameter,))
            return cursor.fetchone()
