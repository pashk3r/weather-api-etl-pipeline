from datetime import date
from typing import Any

import pandas as pd

from src.fields import HOURLY_FIELDS, SILVER_COLUMNS

# Класс для трансформации погоднвых данных 
class WeatherTransformer:
    def transform(self, document: dict[str, Any], processing_date: date) -> list[dict[str, Any]]:
        metadata = document["metadata"]
        hourly = document["raw_response"].get("hourly", {})
        required = {"time", *HOURLY_FIELDS}

        # Проверка на наличие всех необходимых почасовых полей
        if missing := required - set(hourly):
            raise ValueError(f"Отсутствуют почасовые поля: {missing}")

        # Создание DataFrame из почасовых данных
        df = pd.DataFrame(hourly)
        # Проверка на пустой DataFrame
        if df.empty:
            raise ValueError("Почасовые данные пусты")

        # Преобразование времени в UTC и фильтрация данных
        local_time = pd.to_datetime(
            df.pop("time"), 
            format="%Y-%m-%dT%H:%M", 
            errors="coerce", 
        )
        
        # Указываем часовой пояс исходного времени и переводим его в UTC.
        # Неоднозначные и несуществующие местные даты заменяем на NaT.
        df["observation_time"] = (
            local_time.dt.tz_localize(
                "Europe/Minsk",
                nonexistent="NaT",
                ambiguous="NaT",
            ).dt.tz_convert("UTC")
        )

        # Преобразуем погодные показатели в числа, некорректные значения станут пропусками.
        for field in HOURLY_FIELDS:
            df[field] = pd.to_numeric(df[field], errors="coerce")

        # Удаляем записи без корректного времени, температуры или влажности.
        df = df.dropna(subset=["observation_time", "temperature_2m", "relative_humidity_2m"])

        # Оставляем записи за нужную дату по Минску с допустимыми значениями.
        # Для повторяющихся часов сохраняем последнюю строку.
        df = df[
            (local_time.dt.date == processing_date)
            & df["relative_humidity_2m"].between(0, 100)
            & df["temperature_2m"].between(-100, 100)
            & (df["precipitation"] >= 0)
            & (df["wind_speed_10m"] >= 0)
        ].drop_duplicates(subset=["observation_time"], keep="last")

        # Дополняем каждую почасовую запись сведениями о городе и источнике.
        df["city_id"] = metadata["city_id"]
        df["city_name"] = metadata["city"]
        df["source"] = "open-meteo"

        # Форматируем время в строку со смещением UTC для загрузки в PostgreSQL.
        df["observation_time"] = df["observation_time"].dt.strftime("%Y-%m-%dT%H:%M:%S%z")

        return df[list(SILVER_COLUMNS)].to_dict("records")
