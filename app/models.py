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
metadata.reflect(engine, only=['users', 'todo_list', 'todo_management', 'talk_with_wei', 'emotion_garbage_bin', 'daily_diary'])

Base.prepare(engine, reflect=True)

# Automatically generated classes
User = Base.classes.users
Todo = Base.classes.todo_list
TodoMan = Base.classes.todo_management
TalkWei = Base.classes.talk_with_wei
EmoBin = Base.classes.emotion_garbage_bin
DailyDiary = Base.classes.daily_diary