-- Silver-слой хранит очищенные почасовые данные 
-- Gold-слой хранит данные для аналитики
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

-- Таблица в Silver-слое для хранения почасовых наблюдений за погодой в городах
CREATE TABLE IF NOT EXISTS silver.weather_observations (
    city_id INTEGER NOT NULL,
    city_name TEXT NOT NULL,
    observation_time TIMESTAMPTZ NOT NULL,
    temperature_2m REAL NOT NULL,
    relative_humidity_2m INTEGER NOT NULL,
    apparent_temperature REAL,
    precipitation REAL NOT NULL,
    rain REAL,
    snowfall REAL,
    weather_code INTEGER,
    wind_speed_10m REAL NOT NULL,
    wind_direction_10m INTEGER,
    source TEXT NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (city_id, observation_time)
);

-- Таблица в Gold-слое для хранения агрегированных данных о погоде по дням
CREATE TABLE IF NOT EXISTS gold.daily_weather_summary (
    date DATE NOT NULL,
    city_id INTEGER NOT NULL,
    city_name TEXT NOT NULL,
    avg_temperature DOUBLE PRECISION NOT NULL,
    min_temperature REAL NOT NULL,
    max_temperature REAL NOT NULL,
    avg_apparent_temperature DOUBLE PRECISION,
    total_precipitation DOUBLE PRECISION NOT NULL,
    max_wind_speed REAL NOT NULL,
    precipitation_hours INTEGER NOT NULL,
    observation_count INTEGER NOT NULL,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (date, city_id)
);
