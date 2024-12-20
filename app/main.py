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
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
from minio.error import S3Error
import uuid


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
    print("\n\n/register")
    print(user_id, user_email, user_password, department)
    user_data = {
        "user_id":user_id,
        "hashed_password": hashed_password, 
        "user_email": user_email,
        "department":department,
    }
    try:
        # crud.create_record(db, models.User, **user_data)
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
def get_klas(klas_id:str = Form(...), klas_pw:str = Form(...)):
    driver = webdriver.Chrome()  
    
    driver.get("https://klas.kw.ac.kr/usr/cmn/login/LoginForm.do")

    time.sleep(2)

    driver.find_element(By.ID, "loginId").send_keys(klas_id)
    driver.find_element(By.ID, "loginPwd").send_keys(klas_pw)

    time.sleep(1)

    driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div[2]/form/div[2]/button").click()

    time.sleep(2)  

    driver.get("https://klas.kw.ac.kr/std/cps/inqire/AtnlcScreStdPage.do")
    time.sleep(2)

    user_name_element = driver.find_element(By.XPATH, "/html/body/header/div[1]/div/div[2]/a[1]")
    user_name_text = user_name_element.text

    klas_user_name = user_name_text.split('(')[0].strip()  
    klas_user_year = user_name_text.split('(')[1][2:4] 

    print("klas name:", klas_user_name)
    print("klas user year:", klas_user_year)

    tables = driver.find_elements(By.CSS_SELECTOR, ".tablelistbox .AType")

    all_results = {}

    for table in tables:
        headers = table.find_elements(By.CSS_SELECTOR, "thead tr th")
        header_texts = [header.text for header in headers]
        
        rows = table.find_elements(By.CSS_SELECTOR, "tbody tr")
        table_data = []

        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            cell_texts = [cell.text for cell in cells]
            table_data.append(cell_texts)

        if header_texts:  
            all_results[header_texts[0]] = table_data

    print(all_results)

    driver.quit()
    return {klas_user_name, klas_user_year, all_results}










def save_user_taken_lecture_to_db_via_klas(klas_id: str = Form(...), klas_pw: str = Form(...),  db: Session = Depends(get_db)):

    return

# Pydantic 모델 정의 (입력 데이터 검증용)
class ClubCreate(BaseModel):
    area: str
    club_name: str
    instagram: str
    image_logo: str
    joinable: str
    members: int
    image_club: str

@app.post("/add-club", status_code=201)
async def add_club(club: ClubCreate, db: Session = Depends(get_db)):
    # 데이터베이스에 클럽 추가
    try:
        logging.info(club)
        new_club = crud.models.Clubs(
            area=club.area,
            club_name=club.club_name,
            instagram=club.instagram,
            image_logo=club.image_logo,
            joinable=club.joinable,
            members=club.members,
            image_club=club.image_club,
        )
        db.add(new_club)
        db.commit()
        db.refresh(new_club)
        return {"message": "Club added successfully", "club_id": new_club.id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")

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

class BasicClubActivity(BaseModel):
    id: int
    club_id: int
    activity_name: str
    start_at: str
    ends_at: str
    image_activity: str
    about: str

class ClubActivities(BaseModel):
    activities: List[BasicClubActivity]

@app.get("/get-all-club-activity", response_model=ClubActivities)
async def get_all_club_activity(db: Session = Depends(get_db)):
    # club_activity 테이블의 모든 데이터 가져오기
    activities = db.query(crud.models.ClubActivity).all()

    # 결과를 Pydantic 모델로 매핑
    return ClubActivities(
        activities=[
            BasicClubActivity(
                id=activity.id,
                club_id=activity.club_id,
                activity_name=activity.activity_name,
                start_at=activity.start_at.strftime("%Y-%m-%d"),
                ends_at=activity.ends_at.strftime("%Y-%m-%d"),
                image_activity=activity.image_activity,
                about=activity.about,
            )
            for activity in activities
        ]
    )

# Roadmap 관련 Pydantic 모델
class Lecture(BaseModel):
    lec_name: str

class RoadmapItem(BaseModel):
    item: str
    lectures: List[Lecture]

class RoadmapByArea(BaseModel):
    area_name: str
    todos: List[RoadmapItem]

@app.post("/add-roadmap")
async def add_roadmap(data: RoadmapByArea, db: Session = Depends(get_db)):
    try:
        logging.info(data)
        # roadmap_by_area 추가
        new_area = crud.models.RoadmapByArea(
            area_name=data.area_name,
            todos=[]
        )
        db.add(new_area)
        db.commit()
        db.refresh(new_area)

        # roadmap_items 및 lectures 연결
        for todo in data.todos:
            # roadmap_item 추가
            new_item = crud.models.RoadmapItem(
                item=todo.item,
                roadmap_by_area_id=new_area.id
            )
            db.add(new_item)
            db.commit()
            db.refresh(new_item)

            # lectures 리스트 생성 및 추가
            lectures_list = []
            for lecture_filter in todo.lectures:
                # lec_name과 lec_theme을 기반으로 lectures 데이터 검색
                lecture = db.query(crud.models.Lecture).filter(
                    crud.models.Lecture.lec_name == lecture_filter["lec_name"]
                ).first()

                if not lecture:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Lecture with name '{lecture_filter['lec_name']}' and theme '{lecture_filter['lec_theme']}' not found"
                    )

                # 강의 정보를 리스트에 추가
                lectures_list.append(lecture)

            # roadmap_item에 lectures 연결
            new_item.lectures = lectures_list
            db.commit()

        return {"message": "Roadmap added successfully", "id": new_area.id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.get("/get-roadmap/{area_name}", response_model=RoadmapByArea)
async def get_roadmap(area_name: str, db: Session = Depends(get_db)):
    # roadmap_by_area 데이터 가져오기
    area = db.query(RoadmapByArea).filter(RoadmapByArea.area_name == area_name).first()
    if not area:
        raise HTTPException(status_code=404, detail="Roadmap not found")

    # roadmap_items 데이터 가져오기
    todos = db.query(RoadmapItem).filter(RoadmapItem.roadmap_by_area_id == area.id).all()

    # roadmap_items에 연결된 lectures 데이터 가져오기
    todos_with_lectures = []
    for todo in todos:
        lectures = db.query(Lecture).filter(Lecture.roadmap_item_id == todo.id).all()
        todos_with_lectures.append({
            "id": todo.id,
            "item": todo.item,
            "lectures": lectures
        })

    return {
        "id": area.id,
        "area_name": area.area_name,
        "todos": todos_with_lectures
    }

class PresignedUrlResponse(BaseModel):
    url: str  # Presigned URL
    file_name: str  # 생성된 파일 이름
    method: str = "PUT"  # HTTP 메서드 (항상 PUT)

@app.get("/generate-presigned-url", response_model=PresignedUrlResponse)
async def generate_presigned_url():
    """
    Presigned URL을 생성하여 반환하는 API.
    - 파일 이름은 서버에서 UUID 기반으로 생성.
    - Content-Type은 "image/png"로 제한.
    """
    try:
        # MinIO 버킷이 존재하지 않으면 생성
        if not minio_client.bucket_exists(bucket_name):
            minio_client.make_bucket(bucket_name)

        # 고유 파일 이름 생성
        file_name = f"{uuid.uuid4()}.png"

        # Presigned URL 생성
        url = minio_client.presigned_put_object(
            bucket_name=bucket_name,
            object_name=file_name,
            expires=3600  # Presigned URL 유효 시간 (초 단위, 여기선 1시간)
        )

        return PresignedUrlResponse(url=url, file_name=file_name)

    except S3Error as e:
        raise HTTPException(status_code=500, detail=f"MinIO error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")