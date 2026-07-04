from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from schemas.career import CareerAdvice
from utils.prompt_loader import load_prompt

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.7,
)

structured_llm = llm.with_structured_output(CareerAdvice)

career_prompt = load_prompt("career_prompt.txt")

chain = career_prompt | structured_llm


class CareerAgent:

    def get_career_advice(self, goal: str) -> CareerAdvice:
        return chain.invoke({"goal": goal})