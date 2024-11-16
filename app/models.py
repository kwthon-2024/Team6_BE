# models.py
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine, MetaData
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Read DATABASE_URL from .env file
DATABASE_URL = os.getenv("DATABASE_URL")

# Create database engine
engine = create_engine(DATABASE_URL, echo=True)
Base = automap_base()

# Reflect the tables
metadata = MetaData()
metadata.reflect(engine, only=['users', 'taken_lectures', 'lectures', 'graduation_requirements', 'clubs', 'club_activity', 'roadmap_by_area', 'roadmap_items'])

Base.prepare(engine, reflect=True)

# Automatically generated classes
User = Base.classes.users
TakenLectures = Base.classes.taken_lectures
Lectures = Base.classes.lectures
GraduationRequirements = Base.classes.graduation_requirements
Clubs = Base.classes.clubs
ClubActivity = Base.classes.club_activity
RoadmapArea = Base.classes.roadmap_by_area
RoadmapItem = Base.classes.roadmap_items