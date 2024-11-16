from fastapi import FastAPI, Depends, HTTPException, Form, status, Query
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import date
from requests.auth import HTTPBasicAuth
import logging
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from app.database import get_db
from . import crud
from . import models
from . import utils
from sqlalchemy import func, and_
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import re
from typing import List, Set, Dict, Union
from minio import Minio

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.DEBUG)
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Define origins
origins = [
    "http://kwkwiki.duckdns.org",
    "https://kwkwiki.duckdns.org",
    "http://112.152.14.116:1115",
    "http://112.152.14.116:1116"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

minio_client = Minio(
    "118.67.128.129:9000",
    access_key="minio",
    secret_key="minio1234",
    secure=False
)
bucket_name = "kwthon"

@app.middleware("http")
async def add_cors_headers(request, call_next):
    logging.debug(f"Request origin: {request.headers.get('origin')}")
    response = await call_next(request)
    origin = request.headers.get('origin')
    if origin in origins:
        response.headers["Access-Control-Allow-Origin"] = origin
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    logging.debug(f"Response headers: {response.headers}")
    return response

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@app.post("/check-email")
async def check_email(email: str = Form(...), db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, email):
        return {"isDuplicate": True}
    return {"isDuplicate": False}

@app.post("/register")
def register_user(user_id: str = Form(...),  user_email: str = Form(...), user_password:str = Form(...), department:str = Form(...), db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(user_password)
    user_data = {
        "user_id":user_id,
        "hashed_password": hashed_password, 
        "user_email,": user_email,
        "department":department,
    }
    try:
        return crud.get_record_by_id(db, models.User, crud.create_record(db, models.User, **user_data))
    except:
        raise HTTPException(status_code=500, detail="Error creating user")

def authenticate_user(email: str, password: str, db: Session):
    user_id = crud.get_user_by_email(db, email)
    if not user_id:
        return False
    user = crud.get_record_by_id(db, models.User, user_id)
    if not pwd_context.verify(password, user.hashed_password):
        return False
    return user

@app.post("/token")
def login_for_access_token(user_id: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate_user(user_id, password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect user_id or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": utils.create_access_token(data={"user_id": user.user_id}), "token_type": "bearer", "user_id": user.user_id}
    
def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, utils.SECRET_KEY, algorithms=[utils.ALGORITHM])
        user_id: str = payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=403, detail="Token is invalid or expired")
        return payload
    except JWTError:
        raise HTTPException(status_code=403, detail="Token is invalid or expired")

@app.get("/verify-token/{token}")
async def verify_user_token(token: str):
    if utils.is_token_expired(token):
        raise HTTPException(status_code=403, detail="Token is expired")
    verify_token(token=token)
    return {"message": "Token is valid"}

@app.get("/get-graduation-condition/{token}")
def check_graduation_requirements(token: str, db: Session = Depends(get_db)):
    user_id = verify_token(token)
    
    # Get user information
    user_info = crud.get_user_info(db, user_id)
    if not user_info:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_pk, user_entry_year, department = user_info
    
    # Get taken lectures with joined theme and name
    taken_lectures = crud.get_taken_lectures(db, user_pk)
    
    # Get graduation requirements
    grad_requirements = crud.get_graduation_requirements(
        db, 
        year=user_entry_year, 
        department=department
    )
    
    if not grad_requirements:
        raise HTTPException(status_code=404, detail="Graduation requirements not found")
    
    # 4, 5, 6. Calculate credits by classification
    user_taken_major_credit = sum(
        int(lecture.taken_lecture_credit)
        for lecture in taken_lectures
        if lecture.lec_classification in ['전필', '전선']
    )
    
    user_taken_gyo_pill_credit = sum(
        int(lecture.taken_lecture_credit)
        for lecture in taken_lectures
        if lecture.lec_classification == '교필'
    )
    
    user_taken_gyo_sun_credit = sum(
        int(lecture.taken_lecture_credit)
        for lecture in taken_lectures
        if lecture.lec_classification == '교선'
    )
    
    # 7-1, 7-2. Process gyogyun themes
    gyogyun_themes: Set[str] = set()
    for lecture in taken_lectures:
        if lecture.lec_classification == '교선' and lecture.lec_theme:
            # Remove content in parentheses
            theme = re.sub(r'\([^)]*\)', '', lecture.lec_theme).strip()
            gyogyun_themes.add(theme)
    
    required_gyogyun_themes = grad_requirements.gyoGyunTheme.split(',') if grad_requirements.gyoGyunTheme else []
    
    user_taken_require_gyoGyunTheme = []
    user_not_taken_require_gyoGyunTheme = []
    
    for req_theme in required_gyogyun_themes:
        theme_taken = False
        for user_theme in gyogyun_themes:
            if user_theme in req_theme:
                user_taken_require_gyoGyunTheme.append(req_theme)
                theme_taken = True
                break
        if not theme_taken:
            user_not_taken_require_gyoGyunTheme.append(req_theme)
    
    # 8-1, 8-2. Process required lectures
    taken_lecture_names: Set[str] = {
        lecture.lec_name
        for lecture in taken_lectures
        if lecture.lec_classification == '교필' and lecture.lec_name
    }
    
    required_lectures = grad_requirements.gyoPillLecName.split(',') if grad_requirements.gyoPillLecName else []
    
    user_taken_require_gyoPillTheme = []
    user_not_taken_require_gyoPillTheme = []
    
    for req_lecture in required_lectures:
        lecture_taken = False
        for taken_name in taken_lecture_names:
            if taken_name in req_lecture:
                user_taken_require_gyoPillTheme.append(req_lecture)
                lecture_taken = True
                break
        if not lecture_taken:
            user_not_taken_require_gyoPillTheme.append(req_lecture)
    
    # Prepare response
    total_taken_credits = (user_taken_major_credit + 
                         user_taken_gyo_pill_credit + 
                         user_taken_gyo_sun_credit)
    
    return {
        "total_taken_credits": total_taken_credits,
        "major_taken_credits": user_taken_major_credit,
        "gyopill_taken_credits": user_taken_gyo_pill_credit,
        "gyogyun_taken_credits": user_taken_gyo_sun_credit,
        "required_total_credits": grad_requirements.requirementTotalCredit,
        "required_major_credits": grad_requirements.oneMajorCredit,
        "required_gyopill_credits": grad_requirements.gyoPillCredit,
        "required_gyogyun_credits": grad_requirements.gyoGyunCredit,
        "taken_gyogyun_themes": user_taken_require_gyoGyunTheme,
        "not_taken_gyogyun_themes": user_not_taken_require_gyoGyunTheme
    }

@app.put("/save-user-taken-lecture-to-db-via-klas")
def save_user_taken_lecture_to_db_via_klas():
    return

class BasicClass(BaseModel):
    logo_image: str
    club_name: str
    joinable: str

class ClubsByCat(BaseModel):
    clubs: List[BasicClass]

@app.get("/get-clubs-by-category/{category}", response_model=ClubsByCat)
async def get_clubs_by_category(category: str, db: Session = Depends(get_db)):
    # 데이터베이스에서 area가 category와 일치하는 clubs 검색
    clubs = db.query(
        crud.models.Clubs
    ).filter(
        crud.models.Clubs.area == category
    ).all()

    if not clubs:
        raise HTTPException(status_code=404, detail="No clubs found for this category")

    # 검색 결과를 BasicClass 리스트 형태로 변환
    result = [
        BasicClass(
            logo_image=club.image_logo,
            club_name=club.club_name,
            joinable=club.joinable
        )
        for club in clubs
    ]

    return ClubsByCat(clubs=result)

