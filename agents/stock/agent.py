from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm
from agents.stock.stock_tool import get_stock
from dotenv import load_dotenv
import os

load_dotenv()

model = LiteLlm(
    model="openai/gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY"),
)

root_agent = Agent(
    model=model,
    name="stock_agent",
    description="Stock market assistant that provides current price and brief analysis",
    instruction=(
        "You are a concise stock analyst. "
        "When asked about a stock, use the get_stock tool to fetch data. "
        "Always respond in exactly 3 lines: "
        "Line 1: Current price and today's change. "
        "Line 2: Sentiment (Bullish / Bearish / Neutral) with one reason. "
        "Line 3: Simple verdict — Good Buy, Hold, or Avoid — with one short reason. "
        "Keep it brief, clear, and jargon-free."
    ),
    tools=[get_stock]
)
