from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from schemas.resume_review import ResumeReview
from utils.prompt_loader import load_prompt

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.3,
)

# Tell the LLM to return a ResumeReview object
structured_llm = llm.with_structured_output(ResumeReview)

resume_prompt = load_prompt("resume_prompt.txt")

chain = resume_prompt | structured_llm


class ResumeAgent:

    def review_resume(self, resume: str, career_goal: str) -> ResumeReview:
        return chain.invoke(
            {
                "resume": resume,
                "career_goal": career_goal,
            }
        )