from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from models import Base  # Import Base from models.py # Modified import

DATABASE_FILE = Path(__file__).parent.parent / "data" / "hotel.db"

engine = create_engine(f"sqlite:///{DATABASE_FILE}")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_and_tables():
    Base.metadata.create_all(engine)

if __name__ == "__main__":
    create_db_and_tables()
    print(f"Database created at: {DATABASE_FILE}")