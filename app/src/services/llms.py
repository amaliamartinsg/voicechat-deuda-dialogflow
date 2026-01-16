from langchain_openai import ChatOpenAI
from config.project_config import SETTINGS


llm_langchain = ChatOpenAI(
    model=SETTINGS.llm_model_name,
    temperature=SETTINGS.temperature,
    max_retries=SETTINGS.llm_max_retries
)