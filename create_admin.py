# create_admin.py  !!!RUN THIS ONLY ONCE!!!!
import sqlite3
import bcrypt
from sqlalchemy import select
from backend.models import User, Base
from db import get_engine, get_session

def create_initial_admin():
    session = get_session()

    # Check if admin exists
    admin_exists = session.execute(
        select(User).where(User.username == "admin")
    ).scalar_one_or_none()

    if admin_exists is None:
        print("Creating admin user...")
        hashed_password = bcrypt.hashpw("admin".encode(), bcrypt.gensalt())
        admin = User(
            username="admin",
            hashed_password=hashed_password,
            role="Admin",
            full_name="System Administrator",
            phone_number="0000000",
            age=99
        )
        session.add(admin)
        session.commit()
        print("Admin user created successfully.")
    else:
        print("Admin user already exists.")

if __name__ == "__main__":
    # Make sure DB is set up, then create admin if needed
    engine = get_engine()
    Base.metadata.create_all(engine)
    create_initial_admin()
