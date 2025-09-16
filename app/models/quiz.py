from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import JSON, Column, Integer, ForeignKey, UniqueConstraint
from datetime import datetime, timezone

# ===============================
# Quiz Table
# ===============================
class Quiz(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    description: Optional[str] = None
    total_time: int
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    # ✅ New columns
    max_attempts: Optional[int] = Field(default=None, description="Maximum attempts allowed. Null = unlimited")
    is_active: bool = Field(default=True, description="Whether quiz is currently active")
    # Relationships
    questions: List["Question"] = Relationship(
        back_populates="quiz",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    attempts: List["QuizAttempt"] = Relationship(
        back_populates="quiz",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# ===============================
# Question Table
# ===============================
class Question(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_id: int = Field(sa_column=Column(Integer, ForeignKey("quiz.id", ondelete="CASCADE")))
    text: str
    marks: int = 1

    # Relationships
    quiz: "Quiz" = Relationship(back_populates="questions")
    options: List["Option"] = Relationship(
        back_populates="question",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


# ===============================
# Option Table
# ===============================
class Option(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    question_id: int = Field(sa_column=Column(Integer, ForeignKey("question.id", ondelete="CASCADE")))
    text: str
    is_correct: bool = False

    # Relationships
    question: "Question" = Relationship(back_populates="options")


# ===============================
# QuizAttempt Table
# ===============================
class QuizAttempt(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint("quiz_id", "user_id", "attempt_number", name="uq_attempt_number"),
    )
    id: Optional[int] = Field(default=None, primary_key=True)
    quiz_id: int = Field(sa_column=Column(Integer, ForeignKey("quiz.id", ondelete="CASCADE")))
    user_id: int = Field(sa_column=Column(Integer, ForeignKey("user.id", ondelete="CASCADE")))
    attempt_number: int = 1
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    submitted_at: Optional[datetime] = None
    deadline: Optional[datetime] = None   # ✅ NEW FIELD
     
     #✅ Store shuffled order of questions + options
    shuffle_data: Optional[dict] = Field(sa_column=Column(JSON), default=None)

    # Relationships
    quiz: "Quiz" = Relationship(back_populates="attempts")
    answers: List["QuizAnswer"] = Relationship(back_populates="attempt", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    result: Optional["QuizResult"] = Relationship(back_populates="attempt", sa_relationship_kwargs={"cascade": "all, delete-orphan"})


# ===============================
# QuizAnswer Table
# ===============================
class QuizAnswer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    attempt_id: int = Field(sa_column=Column(Integer, ForeignKey("quizattempt.id", ondelete="CASCADE")))
    question_id: int = Field(sa_column=Column(Integer, ForeignKey("question.id", ondelete="CASCADE")))
    selected_option_id: Optional[int] = Field(sa_column=Column(Integer, ForeignKey("option.id", ondelete="SET NULL")))

    # Relationships
    attempt: "QuizAttempt" = Relationship(back_populates="answers")


# ===============================
# QuizResult Table
# ===============================
class QuizResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    attempt_id: int = Field(
        sa_column=Column(Integer, ForeignKey("quizattempt.id", ondelete="CASCADE"), unique=True)
    )
    score: int
    max_score: int
    graded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    # Relationships
    attempt: "QuizAttempt" = Relationship(back_populates="result")
