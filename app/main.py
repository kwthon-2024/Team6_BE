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
from minio import MINIO

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

minio_client = MINIO(
    "118.67.128.129:9000",
    access_key="minio",
    secret_key="minio1234",
    secure=False
)
bucket_name = "test"

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
def register_user(username: str = Form(...), password: str = Form(...), email: str = Form(...), db: Session = Depends(get_db)):
    hashed_password = pwd_context.hash(password)
    user_data = {
        "username": username, 
        "hashed_password": hashed_password, 
        "email": email
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
def login_for_access_token(email: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = authenticate_user(email, password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": utils.create_access_token(data={"email": user.email}), "token_type": "bearer", "email": user.email}
    
def verify_token(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, utils.SECRET_KEY, algorithms=[utils.ALGORITHM])
        email: str = payload.get("email")
        if email is None:
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

