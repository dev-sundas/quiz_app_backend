from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from sqlmodel import Session, select
from app.models.quiz import Question, Quiz, QuizAttempt, QuizResult
from app.models.user import RefreshToken
from sqlalchemy.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from app.schemas.quiz_schema import QuizAnswerRead, QuizAttemptRead

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)




# 1. Save Refresh Token
async def save_refresh_token(session: AsyncSession, user_id: int, token: str, expires_in: int = 7*24*60*60):
    """
    Save a refresh token in DB (default expiry = 7 days).
    """
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    refresh = RefreshToken(user_id=user_id, token=token, expires_at=expires_at)
    session.add(refresh)
    await session.commit()
    await session.refresh(refresh)
    return refresh


# 2. Validate Refresh Token
def is_valid_refresh_token(session: Session, token: str) -> bool:
    """
    Check if refresh token exists, not expired, and not revoked.
    """
    db_token = session.exec(select(RefreshToken).where(RefreshToken.token == token)).first()
    if not db_token:
        return False
    if db_token.revoked:
        return False
    if db_token.expires_at < datetime.utcnow():
        return False
    return True


# 3. Update Refresh Token
def update_refresh_token(session: Session, old_token: str, new_token: str, expires_in: int = 7*24*60*60):
    """
    Replace old refresh token with a new one (rotation).
    """
    db_token = session.exec(select(RefreshToken).where(RefreshToken.token == old_token)).first()
    if not db_token:
        return None
    
    # revoke old one
    db_token.revoked = True
    session.add(db_token)

    # add new one
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    new_refresh = RefreshToken(user_id=db_token.user_id, token=new_token, expires_at=expires_at)
    session.add(new_refresh)

    session.commit()
    session.refresh(new_refresh)
    return new_refresh


# 4. Revoke Refresh Token
def revoke_refresh_token(session: Session, token: str):
    """
    Mark a refresh token as revoked (logout).
    """
    db_token = session.exec(select(RefreshToken).where(RefreshToken.token == token)).first()
    if db_token:
        db_token.revoked = True
        session.add(db_token)
        session.commit()
        return True
    return False


# Force submit an attempt
async def force_submit_attempt(session: AsyncSession, attempt: QuizAttempt) -> QuizAttempt:
    """Force-submit an attempt if deadline passed (unanswered = wrong)."""
    
    # Reload attempt with answers + questions
    result = await session.execute(
        select(QuizAttempt)
        .options(
            selectinload(QuizAttempt.quiz).selectinload(Quiz.questions).selectinload(Question.options),
            selectinload(QuizAttempt.answers)
        )
        .where(QuizAttempt.id == attempt.id)
    )
    attempt = result.scalar_one()

    if attempt.submitted_at is None:
        total_score = 0
        for question in attempt.quiz.questions:
            db_answer = next((a for a in attempt.answers if a.question_id == question.id), None)
            if db_answer and db_answer.selected_option_id:
                selected_option = next((o for o in question.options if o.id == db_answer.selected_option_id), None)
                if selected_option and selected_option.is_correct:
                    total_score += question.marks

        attempt.submitted_at = datetime.utcnow()
        result_obj = QuizResult(
            attempt_id=attempt.id,
            score=total_score,
            max_score=sum(q.marks for q in attempt.quiz.questions),
            graded_at=datetime.utcnow(),
        )
        session.add(result_obj)
        await session.commit()
        await session.refresh(attempt)

    return attempt



def serialize_attempt(attempt: QuizAttempt) -> QuizAttemptRead:
    """Convert QuizAttempt ORM object to QuizAttemptRead Pydantic object with shuffled order."""
    total_points = sum(q.marks for q in attempt.quiz.questions) if attempt.quiz else 0
    elapsed_time = int(((attempt.submitted_at or datetime.utcnow()) - attempt.started_at).total_seconds())

    # ✅ Ensure quiz + shuffle_data exist
    quiz = attempt.quiz
    shuffle_data = attempt.shuffle_data or {}

    # ✅ Build question lookup
    id_to_question = {q.id: q for q in quiz.questions} if quiz else {}

    # ✅ Order questions
    ordered_questions = [id_to_question[qid] for qid in shuffle_data.get("questions", []) if qid in id_to_question]

    # ✅ Build option lookups per question
    question_payload = []
    for q in ordered_questions:
        option_map = {o.id: o for o in q.options}
        option_ids = shuffle_data.get("options", {}).get(str(q.id), [])  # stored as str keys in JSON
        ordered_options = [option_map[oid] for oid in option_ids if oid in option_map]

        question_payload.append({
            "id": q.id,
            "text": q.text,
            "marks": q.marks,
            "options": [{"id": o.id, "text": o.text} for o in ordered_options]
        })

    return QuizAttemptRead(
        id=attempt.id,
        quiz_id=attempt.quiz_id,
        user_id=attempt.user_id,
        started_at=attempt.started_at.replace(tzinfo=timezone.utc),
        submitted_at=attempt.submitted_at.replace(tzinfo=timezone.utc) if attempt.submitted_at else None,
        deadline=attempt.deadline.replace(tzinfo=timezone.utc) if attempt.deadline else None,
        score=getattr(attempt, "score", 0),
        totalPoints=total_points,
        timeSpent=elapsed_time,
        answers=[QuizAnswerRead.model_validate(a) for a in attempt.answers],
        # 🔀 return ordered questions + options in payload
        questions=question_payload,
        shuffle_data=shuffle_data  # <--- add this line
    )

