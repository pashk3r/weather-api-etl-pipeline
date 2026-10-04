HOURLY_FIELDS = (
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "snowfall",
    "weather_code",
    "wind_speed_10m",
    "wind_direction_10m",
)

SILVER_COLUMNS = (
    "city_id",
    "city_name",
    "observation_time",
    *HOURLY_FIELDS,
    "source",
)
 