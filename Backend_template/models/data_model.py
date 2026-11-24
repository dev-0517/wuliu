from datetime import datetime, timezone
from sqlalchemy import String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)

class Base(DeclarativeBase):
    # 小皮可能默认 MyISAM；必须显式启用事务及外键级联。
    __table_args__ = {"mysql_engine": "InnoDB", "mysql_charset": "utf8mb4", "mysql_collate": "utf8mb4_unicode_ci"}

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    nickname: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(default=now)

class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)

class AgreementRecord(Base):
    __tablename__ = "agreement_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String(50))
    agreed_at: Mapped[datetime] = mapped_column(default=now)

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(30))
    description: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[str] = mapped_column(String(30), default="咨询准备")
    analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now, onupdate=now)

class Material(Base):
    __tablename__ = "materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="待补充")
    created_at: Mapped[datetime] = mapped_column(default=now)

class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    case_id: Mapped[int | None] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(100), default="新的案件咨询")
    created_at: Mapped[datetime] = mapped_column(default=now)
    updated_at: Mapped[datetime] = mapped_column(default=now)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    token_usage: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(default=now)


class MessageSource(Base):
    """回答生成时的记录快照；材料修改后仍能回看当时查阅的内容。"""
    __tablename__ = "message_sources"
    message_id: Mapped[int] = mapped_column(ForeignKey("messages.id", ondelete="CASCADE"), primary_key=True)
    sources: Mapped[list] = mapped_column(JSON)


class AnalysisRevision(Base):
    __tablename__ = "analysis_revisions"
    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    analysis: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(default=now)
