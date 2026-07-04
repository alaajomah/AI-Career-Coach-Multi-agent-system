from pydantic import BaseModel, Field


class MissingSkills(BaseModel):
    technical: list[str] = Field(description="Missing technical skills")
    soft: list[str] = Field(description="Missing soft skills")


class SectionRecommendations(BaseModel):
    education: str
    experience: str
    skills: str
    projects: str
    certifications: str


class ResumeReview(BaseModel):
    ats_score: int = Field(description="ATS score out of 100")

    executive_summary: str

    strengths: list[str]

    weaknesses: list[str]

    missing_skills: MissingSkills

    improved_professional_summary: str

    section_recommendations: SectionRecommendations

    recommended_certifications: list[str]

    recommended_projects: list[str]

    final_suggestions: list[str]