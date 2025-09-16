from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime


# ----------------------------
# Question Schemas
# ----------------------------
class QuestionBase(BaseModel):
    text: str
    marks: int

class QuestionCreate(QuestionBase):
    quiz_id: int

class QuestionRead(QuestionBase):
    id: int
    quiz_id: int

class QuestionUpdate(BaseModel):
    text: Optional[str] = None
    marks: Optional[int] = None

# ----------------------------
# Quiz Schemas
# ----------------------------
class QuizBase(BaseModel):
    title: str
    description: Optional[str] = None
    total_time: int
    max_attempts: Optional[int] = None  
    is_active: bool = True

class QuizCreate(QuizBase):
   pass

class QuizRead(QuizBase):
    id: int
    attempts_made: Optional[int] = 0  
    questions: List[QuestionRead] = []
    created_at: datetime
    updated_at: datetime

class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    total_time: Optional[int] = None
    max_attempts: Optional[int] = None  
    is_active: Optional[bool] = None


# ----------------------------
# Option Schemas
# ----------------------------
class OptionBase(BaseModel):
    text: str
    is_correct: bool = False

class OptionCreate(OptionBase):
    question_id: int

class OptionRead(OptionBase):
    id: int
    question_id: int

class OptionUpdate(BaseModel):
    text: Optional[str] = None
    is_correct: Optional[bool] = None


# ----------------------------
# QuizAnswer Schemas
# ----------------------------
class QuizAnswerBase(BaseModel):
    question_id: int
    selected_option_id: Optional[int] = None


class QuizAnswerCreate(QuizAnswerBase):
    attempt_id: int

class QuizAnswerRead(QuizAnswerBase):
    id: int
    attempt_id: int
    question_id: int
    selected_option_id: Optional[int]
    isCorrect: Optional[bool] = None

    class Config:
        from_attributes = True 

# ----------------------------
# QuizAttempt Schemas
# ----------------------------

class QuizAttemptBase(BaseModel):
    quiz_id: int
    attempt_number: int = 1   # student's Nth attempt for this quiz
    deadline: Optional[datetime] = None  # 👈 NEW

class QuizAttemptCreate(QuizAttemptBase):
    pass

class QuizAttemptRead(QuizAttemptBase):
    id: int
    started_at: datetime
    submitted_at: Optional[datetime]
    score: int
    totalPoints: int
    timeSpent: float
    answers: List[QuizAnswerRead]
    shuffle_data: Optional[Dict[str, Any]] = None   # ✅ Optional

class StudentStats(BaseModel):
    totalAttempts: int
    averageScore: float
    bestScore: float
    totalTimeSpent: float

class QuizAttemptUpdate(BaseModel):
    submitted_at: Optional[datetime] = None


# ----------------------------
# QuizResult Schemas
# ----------------------------
class QuizResultBase(BaseModel):
    score: int
    max_score: int

class QuizResultCreate(QuizResultBase):
    attempt_id: int

class QuizResultRead(QuizResultBase):
    id: int
    attempt_id: int
    graded_at: datetime


class QuestionWithOptions(QuestionRead):
    options: List[OptionRead] = []

class QuizWithOptions(QuizRead):
    questions: List[QuestionWithOptions] = []




class QuizAttemptSummary(BaseModel):
    id:int
    attempt_number: int
    score: float
    totalPoints: float
    timeSpent: float  # seconds
    correctAnswers: int
    wrongAnswers: int
    started_at: datetime
    submitted_at: datetime | None


class QuizHistoryRead(BaseModel):
    quiz_id: int
    quiz_title: str
    totalAttempts: int
    averageScore: float
    bestScore: float
    totalTimeSpent: float  # in minutes
    totalQuestions: int
    attempts: List[QuizAttemptSummary]  # per-attempt stats




  
