def get_stock(symbol: str) -> dict:
    """
    Returns mock stock price and sentiment for a given ticker symbol.

    Args:
        symbol: Stock ticker symbol e.g. AAPL, TSLA, GOOGL

    Returns:
        A dictionary with price, change, and a brief market sentiment.
    """
    stock_data = {
        "AAPL":  {"price": 189.30, "change": +1.20, "change_pct": +0.64, "sentiment": "bullish",  "note": "Strong iPhone demand and services growth."},
        "TSLA":  {"price": 177.50, "change": -3.40, "change_pct": -1.88, "sentiment": "bearish",  "note": "Delivery concerns weigh on investor confidence."},
        "GOOGL": {"price": 175.80, "change": +2.10, "change_pct": +1.21, "sentiment": "bullish",  "note": "AI integration boosting search and cloud revenue."},
        "MSFT":  {"price": 415.60, "change": +0.80, "change_pct": +0.19, "sentiment": "neutral",  "note": "Steady growth, Azure cloud remains key driver."},
        "AMZN":  {"price": 192.40, "change": +4.30, "change_pct": +2.28, "sentiment": "bullish",  "note": "AWS and ad revenue hitting record highs."},
        "NVDA":  {"price": 875.40, "change": +12.50, "change_pct": +1.45, "sentiment": "bullish", "note": "AI chip demand remains extremely strong."},
        "META":  {"price": 512.70, "change": -1.60, "change_pct": -0.31, "sentiment": "neutral",  "note": "Ad growth solid but Reality Labs still a drag."},
        "NFLX":  {"price": 632.20, "change": +8.90, "change_pct": +1.43, "sentiment": "bullish",  "note": "Subscriber growth and ad tier performing well."},
        "RELIANCE": {"price": 2945.0, "change": +35.0, "change_pct": +1.20, "sentiment": "bullish", "note": "Retail and Jio segments driving growth."},
        "TCS":   {"price": 3810.0, "change": -22.0, "change_pct": -0.57, "sentiment": "neutral",  "note": "Steady IT demand, deal wins on track."},
        "INFY":  {"price": 1425.0, "change": +18.0, "change_pct": +1.28, "sentiment": "bullish",  "note": "Strong guidance and deal pipeline boost outlook."},
    }

    key = symbol.upper().strip()
    if key in stock_data:
        d = stock_data[key]
        direction = "▲" if d["change"] >= 0 else "▼"
        return {
            "symbol": key,
            "price": d["price"],
            "change": d["change"],
            "change_pct": d["change_pct"],
            "direction": direction,
            "sentiment": d["sentiment"],
            "note": d["note"],
            "status": "success"
        }

    return {
        "symbol": symbol.upper(),
        "status": "not_found",
        "message": f"No data for '{symbol}'. Supported: AAPL, TSLA, GOOGL, MSFT, AMZN, NVDA, META, NFLX, RELIANCE, TCS, INFY"
    }
