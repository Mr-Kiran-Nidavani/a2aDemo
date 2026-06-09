from google.adk.agents.llm_agent import Agent
from remoteAgents.weather.weather_tool import get_weather
from dotenv import load_dotenv
from google.adk.models.lite_llm import LiteLlm
import os

load_dotenv()


model = LiteLlm(
    model="openai/gpt-3.5-turbo",
    api_key=os.getenv("OPENAI_API_KEY"),
)


root_agent = Agent(
    model=model,
    name='weather_agent',
    description='Agent with Custom Tools',
    instruction='A helpful assistant answers user questions on weather.',
    tools=[get_weather] 
)
