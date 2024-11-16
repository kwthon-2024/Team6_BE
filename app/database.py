from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from . import models

# .env 파일에서 환경 변수 로드
load_dotenv()

# .env 파일에서 DATABASE_URL 읽기
DATABASE_URL = os.getenv("DATABASE_URL")

# 데이터베이스 엔진 생성
engine = create_engine(DATABASE_URL)
# 세션 로컬 설정
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
# Base 클래스 생성
models.Base = declarative_base()


def get_db():  # 데이터베이스 세션 생성 함수
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


models.Base.metadata.create_all(bind=engine)
