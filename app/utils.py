from fastapi import  Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, create_model
from sqlalchemy.orm import class_mapper
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional
import os
from dotenv import load_dotenv
from . import crud
from app.database import get_db
from jose import JWTError

load_dotenv()
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 180

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

logging.basicConfig(level=logging.DEBUG)

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)})
    try:
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logging.debug(f"JWT Token created: {encoded_jwt}")
        return encoded_jwt
    except Exception as e:
        logging.error(f"Error encoding JWT token: {e}")
        return None

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logging.debug(f"JWT Token decoded: {payload}")
        return payload
    except jwt.ExpiredSignatureError:
        logging.error("JWT Token has expired")
        raise
    except jwt.InvalidTokenError:
        logging.error("Invalid JWT Token")
        raise

def is_token_expired(token: str) -> bool:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            logging.debug("JWT Token is expired")
            return True
        logging.debug("JWT Token is not expired")
        return False
    except jwt.ExpiredSignatureError:
        logging.debug("JWT Token is expired")
        return True
    except jwt.InvalidTokenError:
        logging.error("Invalid JWT Token")
        return True
    
def verify_user(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        user_data = decode_access_token(token)
        if not user_data:
            raise credentials_exception 
        if is_token_expired(token):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="유효하지 않거나 만료된 토큰")
        user_email = user_data.get("email")
        if not user_email:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, user_email)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없음")
    return user

def sqlalchemy_to_pydantic(model, name: Optional[str] = None) -> BaseModel:
    mapper = class_mapper(model)
    fields = {
        column.key: (column.type.python_type, ...)
        for column in mapper.columns
    }
    pydantic_model = create_model(name or model.__name__, **fields)
    logging.debug(f"Pydantic model created: {pydantic_model}")
    return pydantic_model