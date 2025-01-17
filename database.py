# db.py
import streamlit as st
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base

@st.cache_resource
def get_engine():
    engine = create_engine("sqlite:///hotel_booking.db")  # or full path if you want
    Base.metadata.create_all(engine)
    return engine

@st.cache_resource
def get_session():
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()
