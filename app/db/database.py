#Creates the Engine and Session factory.
from sqlalchemy import create_engine #engine: manager of db connection
from sqlalchemy.orm import sessionmaker #each http get a new session from this factory
import os
from dotenv import load_dotenv

#first load variable from .env
load_dotenv()

#read databse url
DATABASE_URL= os.getenv("DATABASE_URL")

#now create sqlalchemy engine
engine = create_engine(DATABASE_URL)

#create a session factory
SessionLocal = sessionmaker(
    autocommit = False,#so nothing gets saved auto (you have more control)
    autoflush = False, #sqlalchemy wont send any changes auto before every query
    bind = engine, #every session ytou create should use a engine
)

def get_db():
    db=SessionLocal() #creates a actual session
    try:
        yield db #fast api recieves the session here
        #first i used return here then understood concept of yield (resumes function)
    finally:
        db.close() #v imp bcs session remains checkedout and you will run out of avialble connections