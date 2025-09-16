from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.auth.admin import create_admin
from app.db import AsyncSessionLocal, create_db_and_tables
from app.routers.question_router import question_router
from app.routers.quiz_answer_router import quiz_answer_router
from app.routers.quiz_attempt_router import quiz_attempt_router
from app.routers.quiz_result_router import quiz_result_router
from app.routers.quiz_router import quiz_router
from app.routers.option_router import option_router
from app.routers.role_router import role_router
from app.routers.user_router import user_router
from app.auth.login import auth_router

from fastapi.middleware.cors import CORSMiddleware

origins = ["http://localhost:3000","https://quiz-app-eight-ebon-40.vercel.app"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Creating tables..")
    await create_db_and_tables()
    await create_admin()
     # Optional: test DB connection
    retries = 5
    for i in range(retries):
        try:
            async with AsyncSessionLocal() as session:
                await session.execute("SELECT 1")
            print("DB connected!")
            break
        except Exception as e:
            print(f"DB not ready, retry {i+1}/{retries}...", e)
            import asyncio
            await asyncio.sleep(3)
    yield


    
app = FastAPI(lifespan=lifespan)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(role_router)
app.include_router(quiz_router)
app.include_router(question_router)
app.include_router(option_router)
app.include_router(quiz_answer_router)
app.include_router(quiz_attempt_router)
app.include_router(quiz_result_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



