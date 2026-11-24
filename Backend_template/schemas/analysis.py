from typing import Literal
from pydantic import BaseModel, Field, ConfigDict

class StrictResult(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

class FactItem(StrictResult):
    statement: str = Field(min_length=1, max_length=1200)
    source_ref: str = Field(min_length=1, max_length=80)
    quote: str = Field(min_length=1, max_length=800)

class TimelineItem(StrictResult):
    date: str = Field(min_length=1, max_length=100)
    event: str = Field(min_length=1, max_length=2000)
    source: str = Field(min_length=1, max_length=80)
    quote: str = Field(min_length=1, max_length=800)

class RiskItem(StrictResult):
    title: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1200)
    source_refs: list[str] = Field(max_length=10)

class NextStep(StrictResult):
    priority: Literal["优先", "随后"]
    action: str = Field(min_length=1, max_length=600)
    reason: str = Field(min_length=1, max_length=1000)

class AnalysisResult(StrictResult):
    summary: str = Field(min_length=1, max_length=8000)
    facts: list[FactItem] = Field(max_length=12)
    issues: list[str] = Field(max_length=15)
    missing_information: list[str] = Field(max_length=15)
    timeline: list[TimelineItem] = Field(max_length=20)
    suggested_materials: list[str] = Field(max_length=15)
    risks: list[RiskItem] = Field(max_length=8)
    next_steps: list[NextStep] = Field(max_length=8)
    follow_up_questions: list[str] = Field(max_length=5)
