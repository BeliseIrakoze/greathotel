from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.models import Base, User, Service, Package, PackageBooking
import bcrypt
import os

# Get the project root directory
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Create database engine
engine = create_engine(f"sqlite:///{os.path.join(project_root, 'hotel_booking.db')}")

# Create all tables
Base.metadata.drop_all(engine)  # Drop all tables first
Base.metadata.create_all(engine)

# Create a session
Session = sessionmaker(bind=engine)
session = Session()

def create_initial_data():
    print("Creating initial data...")
    
    # Create admin user
    admin = User(
        username="admin",
        hashed_password=bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()),
        role="Admin",
        full_name="System Administrator",
        phone_number="+250700000000",
        age=30,
        email="admin@hotel.com",
        is_active=True
    )
    session.add(admin)
    
    # Create regular user
    user = User(
        username="user",
        hashed_password=bcrypt.hashpw("user123".encode(), bcrypt.gensalt()),
        role="User",
        full_name="John Doe",
        phone_number="+250700000001",
        age=25,
        email="user@example.com",
        is_active=True
    )
    session.add(user)
    
    try:
        session.commit()
        print("Users created successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error creating users: {str(e)}")
        return
    
    # Create sample services
    services = [
        Service(
            name="Deluxe Single Room",
            category="Single",
            description="Comfortable single room with modern amenities",
            price_rwf=50000,
            size="18m²",
            details="Queen-size bed, En-suite bathroom, Air conditioning, Free Wi-Fi",
            max_capacity=1
        ),
        Service(
            name="Premium Double Room",
            category="Double",
            description="Spacious double room with city view",
            price_rwf=80000,
            size="25m²",
            details="King-size bed, En-suite bathroom, Air conditioning, Free Wi-Fi, City view",
            max_capacity=2
        ),
        Service(
            name="Executive Suite",
            category="Suite",
            description="Luxury suite with separate living area",
            price_rwf=150000,
            size="40m²",
            details="King-size bed, Living room, Mini kitchen, Jacuzzi, Free Wi-Fi",
            max_capacity=2
        ),
        Service(
            name="Conference Room A",
            category="Conference",
            description="Modern conference room for business meetings",
            price_rwf=200000,
            size="100m²",
            details="Projector, Sound system, Air conditioning, Free Wi-Fi, Capacity: 50 people",
            max_capacity=50
        ),
        Service(
            name="Spa Access",
            category="Add-on",
            description="Full day access to spa facilities",
            price_rwf=20000,
            size="N/A",
            details="Sauna, Steam room, Massage services available",
            is_add_on=True
        ),
        Service(
            name="Airport Transfer",
            category="Add-on",
            description="Round-trip airport transfer service",
            price_rwf=30000,
            size="N/A",
            details="Luxury vehicle, Professional driver",
            is_add_on=True
        )
    ]
    
    for service in services:
        session.add(service)
    
    try:
        session.commit()
        print("Services created successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error creating services: {str(e)}")
        return
    
    # Create sample packages
    wedding_package = Package(
        name="Elegant Wedding Package",
        category="Wedding",
        description="Complete wedding package including accommodation and venue",
        base_price_rwf=1000000,
        duration_days=2,
        max_guests=100,
        is_customizable=True
    )
    
    conference_package = Package(
        name="Business Conference Package",
        category="Conference",
        description="All-inclusive conference package with accommodation",
        base_price_rwf=500000,
        duration_days=3,
        max_guests=50,
        is_customizable=True
    )
    
    # Add services to packages
    wedding_package.services = [
        services[2],  # Executive Suite
        services[3],  # Conference Room A (as venue)
        services[4],  # Spa Access
        services[5]   # Airport Transfer
    ]
    
    conference_package.services = [
        services[1],  # Premium Double Room
        services[3],  # Conference Room A
        services[5]   # Airport Transfer
    ]
    
    session.add(wedding_package)
    session.add(conference_package)
    
    try:
        session.commit()
        print("Packages created successfully!")
    except Exception as e:
        session.rollback()
        print(f"Error creating packages: {str(e)}")
        return
    
    print("Initial data creation completed!")

if __name__ == "__main__":
    create_initial_data() 