AGENT_CARD = {
    "name": "orchestrator",
    "description": (
        "A multi-skill A2A agent. Routes your request to the right specialist — "
        "ask about city weather or stock prices and analysis."
    ),
    "version": "1.0.0",
    "url": "http://localhost:8000",
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "stateTransitionHistory": False
    },
    "defaultInputModes": ["text"],
    "defaultOutputModes": ["text"],
    "skills": [
        {
            "id": "weather_lookup",
            "name": "Weather Lookup",
            "description": "Current weather conditions for a city",
            "tags": ["weather", "temperature", "city", "climate"],
            "examples": [
                "What is the weather in Bangalore?",
                "How is the weather in Mumbai?"
            ]
        },
        {
            "id": "stock_analysis",
            "name": "Stock Analysis",
            "description": "Current stock price with a 3-line buy/hold/avoid verdict",
            "tags": ["stock", "price", "market", "investment"],
            "examples": [
                "Give me a quick analysis of AAPL",
                "Should I buy TSLA?",
                "How is NVDA doing?"
            ]
        }
    ]
}
