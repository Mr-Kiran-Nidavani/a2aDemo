def get_weather(city: str) -> dict:
    """
    Returns current weather information for a given city.

    Args:
        city: The name of the city to get weather for.

    Returns:
        A dictionary with weather details for the city.
    """
    weather_data = {
        "bangalore":  {"temperature": "26°C", "condition": "Cloudy",  "humidity": "72%", "wind": "12 km/h"},
        "mumbai":     {"temperature": "31°C", "condition": "Humid",   "humidity": "85%", "wind": "18 km/h"},
        "delhi":      {"temperature": "35°C", "condition": "Sunny",   "humidity": "40%", "wind": "8 km/h"},
        "chennai":    {"temperature": "33°C", "condition": "Partly Cloudy", "humidity": "78%", "wind": "14 km/h"},
        "hyderabad":  {"temperature": "29°C", "condition": "Rainy",   "humidity": "80%", "wind": "20 km/h"},
        "kolkata":    {"temperature": "32°C", "condition": "Humid",   "humidity": "82%", "wind": "10 km/h"},
        "pune":       {"temperature": "27°C", "condition": "Sunny",   "humidity": "55%", "wind": "16 km/h"},
    }

    city_key = city.lower().strip()
    if city_key in weather_data:
        data = weather_data[city_key]
        return {
            "city": city.title(),
            "temperature": data["temperature"],
            "condition": data["condition"],
            "humidity": data["humidity"],
            "wind": data["wind"],
            "status": "success"
        }

    return {
        "city": city.title(),
        "status": "not_found",
        "message": f"No weather data available for {city}. Try: Bangalore, Mumbai, Delhi, Chennai, Hyderabad, Kolkata, Pune."
    }
