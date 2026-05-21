# database.py
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# .env에서 URL 가져오기
DATABASE_URL = os.getenv('DATABASE_URL')

# 동기식 데이터베이스 엔진 설정 (psycopg2 기반)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# FastAPI 엔드포인트에서 주입받아 사용할 DB 세션 제너레이터
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()