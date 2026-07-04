from pydantic import BaseModel


class CareerRoadmapStep(BaseModel):
    step: str
    description: str


class CareerProject(BaseModel):
    name: str
    description: str


class Certification(BaseModel):
    name: str
    reason: str


class CareerAdvice(BaseModel):
    career_roadmap: list[CareerRoadmapStep]

    required_skills: list[str]

    recommended_projects: list[CareerProject]

    certifications: list[Certification]