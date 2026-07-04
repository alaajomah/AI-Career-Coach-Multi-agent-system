from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

from schemas.interview import (
    InterviewQuestion,
    InterviewEvaluation,
)
from utils.prompt_loader import load_prompt

load_dotenv()

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0.7,
)

# -----------------------------
# Question Generator
# -----------------------------

question_llm = llm.with_structured_output(
    InterviewQuestion
)

question_prompt = load_prompt(
    "interview_question_prompt.txt"
)

question_chain = question_prompt | question_llm

# -----------------------------
# Answer Evaluation
# -----------------------------

evaluation_llm = llm.with_structured_output(
    InterviewEvaluation
)

evaluation_prompt = load_prompt(
    "interview_evaluation_prompt.txt"
)

evaluation_chain = evaluation_prompt | evaluation_llm

# -----------------------------
# Interview Agent
# -----------------------------

class InterviewAgent:

    def generate_question(
        self,
        job_role: str,
        level: str = "Junior",
        previously_asked: list[str] | None = None,
    ) -> InterviewQuestion:

        previously_asked = previously_asked or []

        # Rendered as a bullet list (or a placeholder line when empty) so
        # the prompt template can just drop {previous_questions} in with
        # an instruction like "Do not repeat or closely rephrase any of
        # the questions listed below."
        if previously_asked:
            previous_questions_text = "\n".join(
                f"- {q}" for q in previously_asked
            )
        else:
            previous_questions_text = "(none yet — this is the first question)"

        return question_chain.invoke(
            {
                "job_role": job_role,
                "level": level,
                "previous_questions": previous_questions_text,
            }
        )

    def evaluate_answer(
        self,
        job_role: str,
        question: str,
        answer: str,
    ) -> InterviewEvaluation:

        return evaluation_chain.invoke(
            {
                "job_role": job_role,
                "question": question,
                "answer": answer,
            }
        )