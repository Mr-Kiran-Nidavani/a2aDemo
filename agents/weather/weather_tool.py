def get_weather(city: str) -> str:
    """
    Mock weather tool.
    """
    weather_data = {
        "bangalore": "26°C, cloudy",
        "mumbai": "31°C, humid",
        "delhi": "35°C, sunny"
    }

    return weather_data.get(
        city.lower(),
        f"No weather data available for {city}"
    )