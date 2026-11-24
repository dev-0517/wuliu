from typing import Literal
from pydantic import BaseModel, Field, field_validator

class CleanModel(BaseModel):
    @field_validator("*", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

class RegisterRequest(CleanModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_@.+-]+$")
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=50)
    agreed: bool

class LoginRequest(CleanModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)

class CaseRequest(CleanModel):
    title: str = Field(min_length=1, max_length=100)
    category: Literal["劳动纠纷", "租房纠纷", "消费纠纷", "合同纠纷", "婚姻家事", "其他"]
    description: str = Field(min_length=10, max_length=12000)
    goal: str = Field(default="", max_length=2000)
    stage: Literal["咨询准备", "协商中", "仲裁中", "一审", "二审", "已结束"] = "咨询准备"

class MaterialRequest(CleanModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=3000)
    status: Literal["已有", "待补充"] = "待补充"

class ConversationRequest(BaseModel):
    case_id: int | None = Field(default=None, gt=0)

class ConversationUpdate(CleanModel):
    title: str = Field(min_length=1, max_length=100)

class ChatRequest(CleanModel):
    content: str = Field(min_length=1, max_length=4000)

class ProfileRequest(CleanModel):
    nickname: str = Field(min_length=1, max_length=50)
