# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    user_pk = Column(Integer, primary_key=True)
    user_id = Column(Text)
    user_name = Column(Text)
    user_entry_year = Column(Integer)

    departments = relationship("Department", back_populates="user")
    taken_lectures = relationship("TakenLecture", back_populates="user")


class Department(Base):
    __tablename__ = 'departments'

    department_pk = Column(Integer, primary_key=True)
    user_pk = Column(Integer, ForeignKey('users.user_pk'))
    department = Column(Text)

    user = relationship("User", back_populates="departments")


class TakenLecture(Base):
    __tablename__ = 'taken_lectures'

    taken_lecture_pk = Column(Integer, primary_key=True)
    user_pk = Column(Integer, ForeignKey('users.user_pk'))
    year = Column(Integer)
    semester = Column(Text)
    lec_number = Column(Text)

    user = relationship("User", back_populates="taken_lectures")
    details = relationship("TakenLectureDetail",
                           back_populates="taken_lecture")


class Lecture(Base):
    __tablename__ = 'lectures'

    lecture_pk = Column(Integer, primary_key=True)
    year = Column(Integer)
    semester = Column(Text)
    lec_number = Column(Text)
    lec_name = Column(Text)
    lec_department = Column(Text)
    lec_theme = Column(Text)


class TakenLectureDetail(Base):
    __tablename__ = 'taken_lecture_details'

    taken_lecture_pk = Column(Integer, ForeignKey(
        'taken_lectures.taken_lecture_pk'), primary_key=True)
    lec_name = Column(Text)
    lec_department = Column(Text)
    lec_theme = Column(Text)
    taken_lecture_credit = Column(Text)

    taken_lecture = relationship("TakenLecture", back_populates="details")


class GraduationRequirements(Base):
    __tablename__ = 'graduation_requirements'

    year = Column(Integer, primary_key=True)
    college = Column(Text)
    department = Column(Text)
    gyoPillCredit = Column(Integer)
    gyoGyunCredit = Column(Integer)
    oneMajorCredit = Column(Integer)
    multipleMajorCredit = Column(Integer)
    deepMajorCredit = Column(Float)
    doubleMajorCredit = Column(Integer)
    minorCredit = Column(Integer)
    requirementTotalCredit = Column(Integer)
    gyoGyunTheme = Column(Text)
    gyoPillLecName = Column(Text)
