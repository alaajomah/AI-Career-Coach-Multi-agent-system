from pydantic import BaseModel, Field


class InterviewQuestion(BaseModel):
    question: str = Field(
        description="A single interview question."
    )


class InterviewEvaluation(BaseModel):
    score: int = Field(
        description="Interview score out of 10."
    )

    strengths: list[str]

    weaknesses: list[str]

    missing_points: list[str]

    improved_answer: str

    final_recommendation: str