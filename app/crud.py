# crud.py
from sqlalchemy.orm import Session
from . import models
import logging
from datetime import date
from sqlalchemy import and_

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# 레코드 생성 함수
def create_record(db: Session, model, **kwargs):
    db_obj = model(**kwargs)
    try:
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        logging.info(f"Successfully created record: {db_obj}")
        return db_obj.id
    except Exception as e:
        db.rollback()  # 예외 발생 시 롤백 수행
        logging.error(f"Error creating record: {e}")
        return False


# 레코드 조회 함수
def get_record_by_id(db: Session, model, record_id: int):
    return db.query(model).filter(model.id == record_id).first()

def get_user_by_email(db: Session, email: str):
    try:
        return db.query(models.User).filter(models.User.email == email).first().id
    except:
        return False
    
def get_id_by_user_and_time(db: Session, model, user_id: int, time: date):
    try:
        return db.query(model).filter((model.user == user_id) and (model.do_when == time)).first().id
    except:
        return False

# 레코드 업데이트 함수
def update_record(db: Session, model, record_id: int, **kwargs):
    try:
        # 개별 키와 값을 unpacking하여 전달
        db.query(model).filter(model.id == record_id).update({**kwargs})
        db.commit()
        logging.info(f"Successfully updated record ID {record_id} in {model.__name__}")
        return True
    except Exception as e:
        logging.error(f"Failed to update record ID {record_id} in {model.__name__}: {e}")
        db.rollback()
        return False

# 레코드 삭제 함수
def delete_record(db: Session, model, record_id: int):
    try:
        db.query(model).filter(model.id == record_id).delete()
        db.commit()
        return True
    except:
        return False
    

def get_user_info(db: Session, user_id: str):
    return db.query(models.User)\
        .with_entities(
            models.User.user_pk,
            models.User.user_entry_year,
            models.User.department
        )\
        .filter(models.User.user_id == user_id)\
        .first()

def get_taken_lectures(db: Session, user_pk: int):
    return db.query(
        models.TakenLecture.taken_lecture_credit,
        models.TakenLecture.lec_classification,
        models.Lecture.lec_theme,
        models.Lecture.lec_name
    ).join(
        models.Lecture,
        and_(
            models.TakenLecture.year == models.Lecture.year,
            models.TakenLecture.semester == models.Lecture.semester,
            models.TakenLecture.lec_number == models.Lecture.lec_number
        ),
        isouter=True
    ).filter(
        models.TakenLecture.user_pk == user_pk
    ).all()

def get_graduation_requirements(db: Session, year: int, department: str):
    return db.query(models.GraduationRequirement)\
        .filter(
            and_(
                models.GraduationRequirement.year == year,
                models.GraduationRequirement.department == department
            )
        )\
        .first()
