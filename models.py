from sqlalchemy import Column, Integer, String, Float, Date, DateTime, ForeignKey, Text, Boolean, Table, LargeBinary
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    phone_number = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # 'admin' or 'user'
    is_active = Column(Boolean, default=True)  # Account status
    created_at = Column(DateTime, default=datetime.utcnow)
    email = Column(String)  # Add email field
    
    bookings = relationship("Booking", back_populates="user")
    package_bookings = relationship("PackageBooking", back_populates="user")

# Association table for packages and services
package_services = Table(
    'package_services',
    Base.metadata,
    Column('package_id', Integer, ForeignKey('packages.package_id'), primary_key=True),
    Column('service_id', Integer, ForeignKey('services.service_id'), primary_key=True)
)

class Package(Base):
    __tablename__ = "packages"
    package_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text)
    base_price_rwf = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # 'Wedding', 'Conference', 'Vacation'
    duration_days = Column(Integer, default=1)
    max_guests = Column(Integer)
    is_customizable = Column(Boolean, default=True)
    cover_image = Column(String)

    services = relationship("Service", secondary=package_services, back_populates="packages")
    bookings = relationship("PackageBooking", back_populates="package")

class Service(Base):
    __tablename__ = "services"
    service_id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)  # e.g., "room", "conference", "massage"
    description = Column(Text)
    price_rwf = Column(Float, nullable=False)
    size = Column(String)  # For rooms (e.g., single, double, suite)
    details = Column(Text)  # Other details
    cover_image = Column(String)  # Path to cover image
    max_capacity = Column(Integer)
    is_add_on = Column(Boolean, default=False)  # Whether this can be added to packages

    images = relationship("ServiceImage", back_populates="service", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="service")
    packages = relationship("Package", secondary=package_services, back_populates="services")

class ServiceImage(Base):
    __tablename__ = "service_images"
    image_id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.service_id", ondelete="CASCADE"))
    image_path = Column(String, nullable=False)
    is_cover = Column(Boolean, default=False)
    caption = Column(String)
    upload_date = Column(DateTime, default=datetime.utcnow)

    service = relationship("Service", back_populates="images")

class Booking(Base):
    __tablename__ = "bookings"
    booking_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    service_id = Column(Integer, ForeignKey("services.service_id"))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_price_rwf = Column(Float, nullable=False)
    booking_status = Column(String, nullable=False, default="pending")  # 'pending', 'approved', 'rejected'
    booking_timestamp = Column(DateTime, default=datetime.utcnow)
    guest_count = Column(Integer, default=1)
    special_requests = Column(Text)

    user = relationship("User", back_populates="bookings")
    service = relationship("Service", back_populates="bookings")

class PackageBooking(Base):
    __tablename__ = "package_bookings"
    booking_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    package_id = Column(Integer, ForeignKey("packages.package_id"))
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    total_price_rwf = Column(Float, nullable=False)
    booking_status = Column(String, nullable=False, default="pending")
    booking_timestamp = Column(DateTime, default=datetime.utcnow)
    guest_count = Column(Integer, nullable=False)
    special_requests = Column(Text)
    selected_services = Column(Text)  # JSON string of selected service IDs

    user = relationship("User", back_populates="package_bookings")
    package = relationship("Package", back_populates="bookings")