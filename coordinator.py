from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from schemas.router import RouterDecision

from agents.career_agent import CareerAgent
from agents.resume_agent import ResumeAgent
from agents.interview_agent import InterviewAgent

from interview_state import (
    start_session,
    has_active_session,
    get_session_context,
    get_asked_questions,
    set_pending_question,
    get_pending_question,
    record_answer,
    end_session,
    END_INTERVIEW_SENTINEL,
)

load_dotenv()

# -------------------------
# Router LLM
# -------------------------

llm = ChatOpenAI(
    model="gpt-4.1-mini",
    temperature=0,
)

router_llm = llm.with_structured_output(RouterDecision)

router_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """
You are a routing system for an AI Career Coach.

Decide which agent should handle the user's request.

Available agents:

- career
  Questions about career advice, roadmap, learning plan,
  certifications, required skills, or career guidance.

- resume
  Resume review, ATS score, CV improvement, resume writing,
  resume feedback.

- interview
  Interview preparation, interview questions,
  mock interviews, interview answer evaluation.

Return the appropriate agent.
            """
        ),
        ("human", "{message}"),
    ]
)

router_chain = router_prompt | router_llm

# -------------------------
# Coordinator Agent
# -------------------------

class CoordinatorAgent:

    def __init__(self):
        self.career_agent = CareerAgent()
        self.resume_agent = ResumeAgent()
        self.interview_agent = InterviewAgent()

    def route(self, message: str) -> str:
        decision = router_chain.invoke(
            {"message": message}
        )
        return decision.agent

    def run(
        self,
        message: str,
        user_id: str,
        user_data: dict | None = None,
    ):
        """
        Returns a dict of shape:
            {"agent": <career|resume|interview|unknown>,
             "type": <advice|review|question|evaluation|session_end|no_session|error>,
             "result": <pydantic-model | dict | str>}
        """

        user_data = user_data or {}

        # -----------------------------------------------------------
        # 0) Explicit "end interview" control signal from the UI.
        #    This is an EXACT match, never inferred from free text,
        #    so a genuine answer can never accidentally end the loop.
        # -----------------------------------------------------------
        if message.strip() == END_INTERVIEW_SENTINEL:
            summary = end_session(user_id)
            if summary is None:
                return {
                    "agent": "interview",
                    "type": "no_session",
                    "result": "There's no active interview session to end.",
                }
            return {
                "agent": "interview",
                "type": "session_end",
                "result": summary,
            }

        # -----------------------------------------------------------
        # 1) If there's an active interview session with a question
        #    pending, THIS message is the answer to it. Evaluate it,
        #    then immediately generate the next question and keep the
        #    session going. No router, no re-analysis of intent.
        # -----------------------------------------------------------
        if has_active_session(user_id):
            pending_question = get_pending_question(user_id)

            if pending_question:
                ctx = get_session_context(user_id)

                evaluation = self.interview_agent.evaluate_answer(
                    job_role=ctx["job_role"],
                    question=pending_question,
                    answer=message,
                )

                record_answer(
                    user_id=user_id,
                    question=pending_question,
                    answer=message,
                    score=evaluation.score,
                    strengths=evaluation.strengths,
                    weaknesses=evaluation.weaknesses,
                )

                next_question = self.interview_agent.generate_question(
                    job_role=ctx["job_role"],
                    level=ctx["level"],
                    previously_asked=get_asked_questions(user_id),
                )

                set_pending_question(user_id, next_question.question)

                return {
                    "agent": "interview",
                    "type": "evaluation",
                    "result": {
                        "evaluation": evaluation,
                        "next_question": next_question
                    },
                }

        # -----------------------------------------------------------
        # 2) No active session and no pending question -> route
        #    normally through the LLM router.
        # -----------------------------------------------------------
        route = self.route(message)

        if route == "career":
            return {
                "agent": "career",
                "type": "advice",
                "result": self.career_agent.get_career_advice(goal=message),
            }

        if route == "resume":
            return {
                "agent": "resume",
                "type": "review",
                "result": self.resume_agent.review_resume(
                    resume=user_data.get("resume", ""),
                    career_goal=user_data.get("career_goal", "AI Engineer"),
                ),
            }

        if route == "interview":
            job_role = user_data.get("career_goal", "AI Engineer")
            level = user_data.get("level", "Junior")

            start_session(user_id, job_role=job_role, level=level)

            question = self.interview_agent.generate_question(
                job_role=job_role,
                level=level,
            )

            set_pending_question(user_id, question.question)

            return {
                "agent": "interview",
                "type": "question",
                "result": question,
            }

        return {
            "agent": "unknown",
            "type": "error",
            "result": "Sorry, I couldn't determine the correct agent.",
        }