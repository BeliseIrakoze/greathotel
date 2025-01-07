import streamlit as st
import bcrypt
import sqlite3
from PIL import Image
import io
import base64
import pandas as pd
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, or_, select, func
from sqlalchemy.orm import sessionmaker
from backend.models import Base, User, Service, ServiceImage, Booking, Package, PackageBooking
import os
import shutil
from pathlib import Path
import json

# Get the project root directory
project_root = os.path.dirname(os.path.abspath(__file__))

# Create images directory if it doesn't exist
IMAGES_DIR = os.path.join(project_root, "static", "images")
os.makedirs(IMAGES_DIR, exist_ok=True)

# Database connection
engine = create_engine(f"sqlite:///{os.path.join(project_root, 'hotel_booking.db')}")
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Set the app name and favicon
app_name = "Hotel Booking System"
favicon_emoji = "🏨"
st.set_page_config(page_title=app_name, page_icon=favicon_emoji, layout="wide")

def save_uploaded_image(uploaded_file, service_id, is_cover=False):
    if uploaded_file is None:
        return None
    
    # Create service directory if it doesn't exist
    service_dir = os.path.join(IMAGES_DIR, str(service_id))
    os.makedirs(service_dir, exist_ok=True)
    
    # Generate unique filename
    file_ext = Path(uploaded_file.name).suffix
    filename = f"{'cover' if is_cover else datetime.now().strftime('%Y%m%d_%H%M%S')}{file_ext}"
    file_path = os.path.join(service_dir, filename)
    
    # Save the file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    # Return relative path from project root
    return os.path.join("static", "images", str(service_id), filename).replace("\\", "/")

def delete_service_image(image_path):
    if image_path:
        full_path = os.path.join(project_root, image_path)
        try:
            os.remove(full_path)
        except FileNotFoundError:
            pass

def create_user(username, password, role):
    hashed_password = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    user = User(
        username=username,
        hashed_password=hashed_password,
        role=role
    )
    try:
        session.add(user)
        session.commit()
        return "User created successfully."
    except Exception as e:
        session.rollback()
        return f"Error creating user: {str(e)}"

def authenticate_user_role(username, password, role):
    user = session.execute(
        select(User).where(
            User.username == username,
            User.role == role
        )
    ).scalar_one_or_none()
    
    if user and bcrypt.checkpw(password.encode(), user.hashed_password):
        return True
    return False

def authenticate_admin(username, password):
    return authenticate_user_role(username, password, "Admin")

def authenticate_user(username, password):
    return authenticate_user_role(username, password, "User")

def get_available_services(start_date, end_date, category=None):
    stmt = select(Service)
    if category and category != "All":
        stmt = stmt.where(Service.category == category)
    
    booked_services_stmt = select(Service.service_id).join(Booking).where(
        Booking.start_date <= end_date,
        Booking.end_date >= start_date,
        Booking.booking_status == "approved"
    )
    
    stmt = stmt.where(~Service.service_id.in_(booked_services_stmt))
    return session.execute(stmt).scalars().all()

def create_booking(user_id, service_id, start_date, end_date, total_price):
    booking = Booking(
        user_id=user_id,
        service_id=service_id,
        start_date=start_date,
        end_date=end_date,
        total_price_rwf=total_price,
        booking_status="pending"
    )
    session.add(booking)
    session.commit()
    return booking

def get_user_bookings(username):
    stmt = select(Booking).join(User).where(User.username == username)
    return session.execute(stmt).scalars().all()

def get_all_bookings():
    stmt = select(Booking)
    return session.execute(stmt).scalars().all()

# User authentication state
if "authentication_status" not in st.session_state:
    st.session_state.authentication_status = None
if "username" not in st.session_state:
    st.session_state.username = None
if "role" not in st.session_state:
    st.session_state.role = None

def login():
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.title("Login")
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        role = st.selectbox("Role", ["User", "Admin"])

        if st.button("Login"):
            if role == "Admin":
                auth_status = authenticate_admin(username, password)
            else:
                auth_status = authenticate_user(username, password)

            if auth_status:
                # Check if account is active (for users only)
                if role == "User":
                    user = session.execute(
                        select(User).where(User.username == username)
                    ).scalar_one_or_none()
                    if not user.is_active:
                        st.error("Your account has been disabled. Please contact admin.")
                        return
                
                st.session_state.authentication_status = True
                st.session_state.username = username
                st.session_state.role = role
                st.success("Login successful")
                st.rerun()
            else:
                st.error("Username or password is incorrect")
    
    with tab2:
        st.title("Sign Up")
        with st.form("signup_form"):
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            full_name = st.text_input("Full Name")
            phone_number = st.text_input("Phone Number")
            age = st.number_input("Age", min_value=1, max_value=120)
            
            if st.form_submit_button("Sign Up"):
                if new_password != confirm_password:
                    st.error("Passwords do not match!")
                    return
                
                if age < 18:
                    st.error("You must be 18 or older to register!")
                    return
                
                try:
                    hashed_password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt())
                    user = User(
                        username=new_username,
                        hashed_password=hashed_password,
                        role="User",
                        full_name=full_name,
                        phone_number=phone_number,
                        age=age
                    )
                    session.add(user)
                    session.commit()
                    st.success("Account created successfully! Please login.")
                except Exception as e:
                    st.error(f"Error creating account: {str(e)}")

def logout():
    st.session_state.authentication_status = None
    st.session_state.username = None
    st.session_state.role = None
    st.rerun()

def display_image_safely(image_path, use_container_width=True):
    """Safely display an image with error handling"""
    try:
        if image_path:
            st.image(image_path, use_container_width=use_container_width)
        else:
            st.info("No image available")
    except Exception:
        st.info("Image not available")

def home_page():
    st.title("Welcome to Our Hotel")
    st.write("Book your perfect stay with us!")

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Check-in Date", min_value=date.today())
    with col2:
        end_date = st.date_input("Check-out Date", min_value=start_date or date.today())

    category = st.selectbox("Room Type", ["All", "Single", "Double", "Suite", "Conference"])

    available_services = get_available_services(start_date, end_date, category)
    
    if available_services:
        st.subheader("Available Rooms")
        
        st.markdown("""
        <style>
        .service-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            height: 100%;
        }
        .service-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transform: translateY(-2px);
            transition: all 0.3s ease;
        }
        .service-card h3 {
            margin: 0;
            color: #1f1f1f;
        }
        .service-card p {
            margin: 5px 0;
            color: #666;
        }
        .service-price {
            font-size: 1.2em;
            color: #2e7d32;
            font-weight: bold;
        }
        </style>
        """, unsafe_allow_html=True)
        
        cols = st.columns(3)
        for idx, service in enumerate(available_services):
            with cols[idx % 3]:
                with st.container():
                    display_image_safely(service.cover_image)
                    
                    st.markdown(f"""
                    <div class="service-card">
                        <h3>{service.name}</h3>
                        <p class="service-price">{service.price_rwf:,.0f} RWF/night</p>
                        <p><strong>Size:</strong> {service.size}</p>
                        <p><strong>Max Guests:</strong> {service.max_capacity or 1}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if st.button("View Details", key=f"view_{service.service_id}"):
                        st.session_state.selected_service = service.service_id
                        st.rerun()
    else:
        st.warning("No available rooms found for the selected dates and category.") 

def add_service_image(service_id, image_file, caption=""):
    image_path = save_uploaded_image(image_file, service_id)
    if image_path:
        service_image = ServiceImage(
            service_id=service_id,
            image_path=image_path,
            caption=caption
        )
        session.add(service_image)
        session.commit()

def delete_service(service_id):
    service = session.get(Service, service_id)
    if service:
        # Delete all images from filesystem
        if service.cover_image:
            delete_service_image(service.cover_image)
        for image in service.images:
            delete_service_image(image.image_path)
        
        # Delete service directory
        service_dir = os.path.join(IMAGES_DIR, str(service_id))
        shutil.rmtree(service_dir, ignore_errors=True)
        
        # Delete from database
        session.delete(service)
        session.commit()

def service_management_page():
    st.header("Service Management")
    
    # Create new service
    with st.expander("➕ Add New Service", expanded=False):
        with st.form("new_service_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Service Name")
                category = st.selectbox("Category", ["Single", "Double", "Suite", "Conference", "Add-on"])
                price_rwf = st.number_input("Price (RWF)", min_value=0, step=1000)
                size = st.text_input("Size (e.g., 18m²)")
                max_capacity = st.number_input("Max Capacity", min_value=1, value=1)
            
            with col2:
                description = st.text_area("Description")
                details = st.text_area("Details")
                is_add_on = st.checkbox("Is Add-on Service", value=category == "Add-on")
                cover_image = st.file_uploader("Cover Image", type=["jpg", "jpeg", "png"])
            
            if st.form_submit_button("Create Service", use_container_width=True):
                if all([name, category, description, price_rwf > 0, size, details]):
                    try:
                        service = Service(
                            name=name,
                            category=category,
                            description=description,
                            price_rwf=price_rwf,
                            size=size,
                            details=details,
                            max_capacity=max_capacity,
                            is_add_on=is_add_on
                        )
                        session.add(service)
                        session.commit()

                        # Handle cover image
                        if cover_image:
                            image_path = save_uploaded_image(cover_image, service.service_id, is_cover=True)
                            service.cover_image = image_path
                            session.commit()

                        st.success("Service created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating service: {str(e)}")
                else:
                    st.error("Please fill in all required fields.")
    
    # Manage existing services
    st.subheader("Manage Services")
    services = session.execute(select(Service)).scalars().all()
    
    # Group services by category
    service_categories = {}
    for service in services:
        if service.category not in service_categories:
            service_categories[service.category] = []
        service_categories[service.category].append(service)
    
    # Display services by category
    for category, category_services in service_categories.items():
        st.markdown(f"### {category}")
        
        for service in category_services:
            with st.expander(f"🏨 {service.name}", expanded=False):
                tab1, tab2 = st.tabs(["📝 Details", "🖼️ Images"])
                
                with tab1:
                    with st.form(f"edit_service_{service.service_id}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            name = st.text_input("Service Name", value=service.name)
                            category = st.selectbox("Category", 
                                                ["Single", "Double", "Suite", "Conference", "Add-on"],
                                                index=["Single", "Double", "Suite", "Conference", "Add-on"].index(service.category))
                            price_rwf = st.number_input("Price (RWF)", 
                                                    min_value=0, 
                                                    value=int(service.price_rwf),
                                                    step=1000)
                            size = st.text_input("Size", value=service.size)
                            max_capacity = st.number_input("Max Capacity", 
                                                        min_value=1, 
                                                        value=service.max_capacity or 1)
                        
                        with col2:
                            description = st.text_area("Description", value=service.description)
                            details = st.text_area("Details", value=service.details)
                            is_add_on = st.checkbox("Is Add-on Service", value=service.is_add_on)
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            update = st.form_submit_button("💾 Save Changes", use_container_width=True)
                        with col2:
                            delete = st.form_submit_button("🗑️ Delete Service", type="secondary", use_container_width=True)
                        
                        if update:
                            try:
                                service.name = name
                                service.category = category
                                service.description = description
                                service.price_rwf = float(price_rwf)
                                service.size = size
                                service.details = details
                                service.max_capacity = max_capacity
                                service.is_add_on = is_add_on
                                
                                session.commit()
                                st.success("Service updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating service: {str(e)}")
                        
                        elif delete:
                            if st.session_state.get(f"confirm_delete_svc_{service.service_id}"):
                                delete_service(service.service_id)
                                st.success("Service deleted successfully!")
                                st.rerun()
                            else:
                                st.session_state[f"confirm_delete_svc_{service.service_id}"] = True
                                st.warning("Click delete again to confirm.")
                
                with tab2:
                    # Cover image
                    st.subheader("Cover Image")
                    display_image_safely(service.cover_image)
                    
                    with st.form(f"update_cover_{service.service_id}"):
                        uploaded_file = st.file_uploader("Upload Cover Image", type=["jpg", "jpeg", "png"])
                        if st.form_submit_button("Update Cover Image", use_container_width=True) and uploaded_file:
                            try:
                                if service.cover_image:
                                    delete_service_image(service.cover_image)
                                image_path = save_uploaded_image(uploaded_file, service.service_id, is_cover=True)
                                service.cover_image = image_path
                                session.commit()
                                st.success("Cover image updated!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error updating cover image: {str(e)}")
                    
                    # Gallery
                    st.subheader("Image Gallery")
                    if service.images:
                        gallery_cols = st.columns(3)
                        for idx, image in enumerate(service.images):
                            with gallery_cols[idx % 3]:
                                display_image_safely(image.image_path)
                                if st.button("🗑️", key=f"del_img_{image.image_id}"):
                                    try:
                                        delete_service_image(image.image_path)
                                        session.delete(image)
                                        session.commit()
                                        st.success("Image deleted!")
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Error deleting image: {str(e)}")
                    else:
                        st.info("No images in the gallery yet")
                    
                    # Add new images
                    with st.form(f"add_images_{service.service_id}"):
                        uploaded_files = st.file_uploader(
                            "Add Gallery Images",
                            type=["jpg", "jpeg", "png"],
                            accept_multiple_files=True
                        )
                        caption = st.text_input("Caption (optional)")
                        
                        if st.form_submit_button("Add Images", use_container_width=True) and uploaded_files:
                            try:
                                for img in uploaded_files:
                                    add_service_image(service.service_id, img, caption)
                                st.success("Images added successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error adding images: {str(e)}")

def package_management_page():
    st.header("Package Management")
    
    # Create new package
    with st.expander("➕ Add New Package", expanded=False):
        with st.form("new_package_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Package Name")
                category = st.selectbox("Category", ["Wedding", "Conference"])
                base_price = st.number_input("Base Price (RWF)", min_value=0, step=1000)
                duration_days = st.number_input("Duration (Days)", min_value=1, value=1)
                max_guests = st.number_input("Max Guests", min_value=1, value=1)
            
            with col2:
                description = st.text_area("Description")
                is_customizable = st.checkbox("Is Customizable", value=True)
                cover_image = st.file_uploader("Cover Image", type=["jpg", "jpeg", "png"])
                
                # Select services to include
                available_services = session.execute(select(Service)).scalars().all()
                service_options = {s.name: s for s in available_services}
                selected_services = st.multiselect(
                    "Include Services",
                    options=list(service_options.keys())
                )
            
            if st.form_submit_button("Create Package", use_container_width=True):
                if all([name, category, base_price > 0, description, selected_services]):
                    try:
                        package = Package(
                            name=name,
                            category=category,
                            description=description,
                            base_price_rwf=base_price,
                            duration_days=duration_days,
                            max_guests=max_guests,
                            is_customizable=is_customizable
                        )
                        
                        # Add selected services
                        for service_name in selected_services:
                            package.services.append(service_options[service_name])
                        
                        session.add(package)
                        session.commit()

                        # Handle cover image
                        if cover_image:
                            image_path = save_uploaded_image(cover_image, package.package_id, is_cover=True)
                            package.cover_image = image_path
                            session.commit()

                        st.success("Package created successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error creating package: {str(e)}")
                else:
                    st.error("Please fill in all required fields.")
    
    # Manage existing packages
    st.subheader("Manage Packages")
    packages = session.execute(select(Package)).scalars().all()
    
    for package in packages:
        with st.expander(f"📦 {package.name} ({package.category})", expanded=False):
            tab1, tab2, tab3 = st.tabs(["📝 Details", "🖼️ Images", "🛠️ Services"])
            
            with tab1:
                with st.form(f"edit_package_{package.package_id}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        name = st.text_input("Package Name", value=package.name)
                        category = st.selectbox("Category", 
                                            ["Wedding", "Conference"],
                                            index=["Wedding", "Conference"].index(package.category))
                        base_price = st.number_input("Base Price (RWF)", 
                                                min_value=0, 
                                                value=int(package.base_price_rwf),
                                                step=1000)
                        duration_days = st.number_input("Duration (Days)", 
                                                    min_value=1, 
                                                    value=package.duration_days)
                        max_guests = st.number_input("Max Guests", 
                                                min_value=1, 
                                                value=package.max_guests)
                    
                    with col2:
                        description = st.text_area("Description", value=package.description)
                        is_customizable = st.checkbox("Is Customizable", value=package.is_customizable)
                        
                        # Select services to include
                        available_services = session.execute(select(Service)).scalars().all()
                        service_options = {s.name: s for s in available_services}
                        current_services = [s.name for s in package.services]
                        selected_services = st.multiselect(
                            "Include Services",
                            options=list(service_options.keys()),
                            default=current_services
                        )
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        update = st.form_submit_button("💾 Save Changes", use_container_width=True)
                    with col2:
                        delete = st.form_submit_button("🗑️ Delete Package", type="secondary", use_container_width=True)
                    
                    if update:
                        try:
                            package.name = name
                            package.category = category
                            package.description = description
                            package.base_price_rwf = float(base_price)
                            package.duration_days = duration_days
                            package.max_guests = max_guests
                            package.is_customizable = is_customizable
                            
                            # Update services
                            package.services = [service_options[name] for name in selected_services]
                            
                            session.commit()
                            st.success("Package updated successfully!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating package: {str(e)}")
                    
                    elif delete:
                        if st.session_state.get(f"confirm_delete_pkg_{package.package_id}"):
                            if package.cover_image:
                                delete_service_image(package.cover_image)
                            session.delete(package)
                            session.commit()
                            st.success("Package deleted successfully!")
                            st.rerun()
                        else:
                            st.session_state[f"confirm_delete_pkg_{package.package_id}"] = True
                            st.warning("Click delete again to confirm.")
            
            with tab2:
                # Cover image
                st.subheader("Cover Image")
                display_image_safely(package.cover_image)
                
                with st.form(f"update_cover_{package.package_id}"):
                    uploaded_file = st.file_uploader("Upload Cover Image", type=["jpg", "jpeg", "png"])
                    if st.form_submit_button("Update Cover Image", use_container_width=True) and uploaded_file:
                        try:
                            if package.cover_image:
                                delete_service_image(package.cover_image)
                            image_path = save_uploaded_image(uploaded_file, package.package_id, is_cover=True)
                            package.cover_image = image_path
                            session.commit()
                            st.success("Cover image updated!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error updating cover image: {str(e)}")
            
            with tab3:
                # Manage included services
                st.subheader("Included Services")
                service_cols = st.columns(3)
                for idx, service in enumerate(package.services):
                    with service_cols[idx % 3]:
                        display_image_safely(service.cover_image)
                        st.markdown(f"""
                        <div style='text-align: center'>
                            <p><strong>{service.name}</strong></p>
                            <p>{service.price_rwf:,.0f} RWF</p>
                            <p><small>{service.category}</small></p>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Add-on services
                if package.is_customizable:
                    st.subheader("Available Add-ons")
                    add_on_services = session.execute(
                        select(Service).where(
                            Service.is_add_on == True,
                            ~Service.service_id.in_([s.service_id for s in package.services])
                        )
                    ).scalars().all()
                    
                    if add_on_services:
                        addon_cols = st.columns(2)
                        for idx, service in enumerate(add_on_services):
                            with addon_cols[idx % 2]:
                                if service.cover_image:
                                    st.image(service.cover_image, use_container_width=True)
                                st.markdown(f"""
                                <div style='text-align: center'>
                                    <p><strong>{service.name}</strong></p>
                                    <p>{service.price_rwf:,.0f} RWF</p>
                                    <p><small>{service.description}</small></p>
                                </div>
                                """, unsafe_allow_html=True)

def user_management_page():
    st.header("User Management")
    
    # Get all users
    users = session.execute(select(User)).scalars().all()
    
    # Display users in a grid
    st.subheader("User List")
    for user in users:
        with st.expander(f"User: {user.username} ({user.role})"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"Full Name: {user.full_name}")
                st.write(f"Phone: {user.phone_number}")
                st.write(f"Age: {user.age}")
                st.write(f"Created: {user.created_at.strftime('%Y-%m-%d')}")
            
            with col2:
                st.write(f"Status: {'Active' if user.is_active else 'Disabled'}")
                # Booking counts
                booking_count = session.execute(
                    select(func.count()).select_from(Booking).where(Booking.user_id == user.user_id)
                ).scalar()
                package_booking_count = session.execute(
                    select(func.count()).select_from(PackageBooking).where(PackageBooking.user_id == user.user_id)
                ).scalar()
                st.write(f"Service Bookings: {booking_count}")
                st.write(f"Package Bookings: {package_booking_count}")
            
            # Action buttons
            if user.username != "admin":  # Prevent actions on admin account
                col1, col2 = st.columns(2)
                with col1:
                    if user.is_active:
                        if st.button("Disable Account", key=f"disable_{user.user_id}"):
                            user.is_active = False
                            session.commit()
                            st.success("Account disabled!")
                            st.rerun()
                    else:
                        if st.button("Enable Account", key=f"enable_{user.user_id}"):
                            user.is_active = True
                            session.commit()
                            st.success("Account enabled!")
                            st.rerun()
                
                with col2:
                    if st.button("Delete Account", key=f"delete_{user.user_id}"):
                        session.delete(user)
                        session.commit()
                        st.success("Account deleted!")
                        st.rerun()

def booking_history_page():
    st.title("Booking History")
    
    # Tabs for different booking types
    tab1, tab2 = st.tabs(["Service Bookings", "Package Bookings"])
    
    with tab1:
        if st.session_state.role == "Admin":
            bookings = session.execute(select(Booking)).scalars().all()
            st.subheader("All Service Bookings")
        else:
            bookings = get_user_bookings(st.session_state.username)
            st.subheader("Your Service Bookings")

        for booking in bookings:
            with st.expander(f"Booking {booking.booking_id} - {booking.booking_status.upper()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"Service: {booking.service.name}")
                    st.write(f"Check-in: {booking.start_date}")
                    st.write(f"Check-out: {booking.end_date}")
                    st.write(f"Total Price: {booking.total_price_rwf:,.0f} RWF")
                
                with col2:
                    if st.session_state.role == "Admin":
                        user = booking.user
                        st.write(f"Booked by: {user.full_name}")
                        st.write(f"Phone: {user.phone_number}")
                        st.write(f"Age: {user.age}")
                
                if booking.special_requests:
                    st.write("Special Requests:", booking.special_requests)
                
                if booking.booking_status == "pending":
                    if st.session_state.role == "Admin":
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Approve", key=f"approve_{booking.booking_id}"):
                                booking.booking_status = "approved"
                                session.commit()
                                st.success("Booking approved!")
                                st.rerun()
                        with col2:
                            if st.button("Reject", key=f"reject_{booking.booking_id}"):
                                booking.booking_status = "rejected"
                                session.commit()
                                st.success("Booking rejected!")
                                st.rerun()
                    else:
                        if st.button("Cancel Booking", key=f"cancel_{booking.booking_id}"):
                            session.delete(booking)
                            session.commit()
                            st.success("Booking cancelled!")
                            st.rerun()
    
    with tab2:
        if st.session_state.role == "Admin":
            package_bookings = session.execute(select(PackageBooking)).scalars().all()
            st.subheader("All Package Bookings")
        else:
            user = session.execute(
                select(User).where(User.username == st.session_state.username)
            ).scalar_one_or_none()
            if user:
                package_bookings = session.execute(
                    select(PackageBooking).where(PackageBooking.user_id == user.user_id)
                ).scalars().all()
                st.subheader("Your Package Bookings")

        for booking in package_bookings:
            with st.expander(f"Package Booking {booking.booking_id} - {booking.booking_status.upper()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"Package: {booking.package.name}")
                    st.write(f"Start Date: {booking.start_date}")
                    st.write(f"End Date: {booking.end_date}")
                    st.write(f"Total Price: {booking.total_price_rwf:,.0f} RWF")
                    st.write(f"Guest Count: {booking.guest_count}")
                
                with col2:
                    if st.session_state.role == "Admin":
                        user = booking.user
                        st.write(f"Booked by: {user.full_name}")
                        st.write(f"Phone: {user.phone_number}")
                        st.write(f"Age: {user.age}")
                    
                    # Show selected services
                    selected_services = json.loads(booking.selected_services)
                    services = session.execute(
                        select(Service).where(Service.service_id.in_(selected_services))
                    ).scalars().all()
                    st.write("Selected Services:")
                    for service in services:
                        st.write(f"- {service.name}")
                
                if booking.special_requests:
                    st.write("Special Requests:", booking.special_requests)
                
                if booking.booking_status == "pending":
                    if st.session_state.role == "Admin":
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("Approve", key=f"approve_pkg_{booking.booking_id}"):
                                booking.booking_status = "approved"
                                session.commit()
                                st.success("Booking approved!")
                                st.rerun()
                        with col2:
                            if st.button("Reject", key=f"reject_pkg_{booking.booking_id}"):
                                booking.booking_status = "rejected"
                                session.commit()
                                st.success("Booking rejected!")
                                st.rerun()
                    else:
                        if st.button("Cancel Booking", key=f"cancel_pkg_{booking.booking_id}"):
                            session.delete(booking)
                            session.commit()
                            st.success("Booking cancelled!")
                            st.rerun()

def packages_page():
    st.title("Event Packages")
    
    # Filter packages by category
    category = st.selectbox("Category", ["All", "Wedding", "Conference"])
    
    # Get packages
    stmt = select(Package)
    if category != "All":
        stmt = stmt.where(Package.category == category)
    packages = session.execute(stmt).scalars().all()
    
    if packages:
        # CSS for package cards
        st.markdown("""
        <style>
        .package-card {
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .package-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            transform: translateY(-2px);
            transition: all 0.3s ease;
        }
        .package-card h3 {
            margin: 0;
            color: #1f1f1f;
            margin-bottom: 10px;
        }
        .package-card p {
            margin: 5px 0;
            color: #666;
        }
        .package-price {
            font-size: 1.2em;
            color: #2e7d32;
            font-weight: bold;
            margin: 10px 0;
        }
        .included-services {
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #eee;
        }
        .service-item {
            padding: 5px 0;
            color: #555;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Display packages in a grid
        cols = st.columns(2)
        for idx, package in enumerate(packages):
            with cols[idx % 2]:
                with st.container():
                    # Display cover image
                    display_image_safely(package.cover_image)
                    
                    st.markdown(f"""
                    <div class="package-card">
                        <h3>{package.name}</h3>
                        <p class="package-price">{package.base_price_rwf:,.0f} RWF</p>
                        <p><strong>Category:</strong> {package.category}</p>
                        <p><strong>Duration:</strong> {package.duration_days} day{'s' if package.duration_days > 1 else ''}</p>
                        <p><strong>Max Guests:</strong> {package.max_guests}</p>
                        <p>{package.description}</p>
                        <div class="included-services">
                            <p><strong>Included Services:</strong></p>
                    """, unsafe_allow_html=True)
                    
                    # Display included services
                    for service in package.services:
                        st.markdown(f"""
                        <div class="service-item">
                            • {service.name} ({service.category}) - {service.price_rwf:,.0f} RWF
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("</div></div>", unsafe_allow_html=True)
                    
                    # Preview included services with images
                    if package.services:
                        st.write("Service Previews:")
                        service_cols = st.columns(3)
                        for sidx, service in enumerate(package.services):
                            with service_cols[sidx % 3]:
                                display_image_safely(service.cover_image)
                                st.caption(service.name)
                    
                    # View Details button
                    if st.button("View Details", key=f"view_package_{package.package_id}"):
                        st.session_state.selected_package = package.package_id
                        st.rerun()
    else:
        st.warning("No packages found.")

def service_details_page(service_id):
    # Back button
    if st.button("← Back to Services"):
        del st.session_state.selected_service
        st.rerun()
    
    service = session.get(Service, service_id)
    if not service:
        st.error("Service not found!")
        return
    
    # Main content in horizontal layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.title(service.name)
        
        # Display cover image
        if service.cover_image:
            st.image(service.cover_image, use_container_width=True)
        
        # Display gallery images in tabs
        if service.images:
            st.subheader("Image Gallery")
            gallery_cols = st.columns(3)
            for idx, image in enumerate(service.images):
                with gallery_cols[idx % 3]:
                    st.image(image.image_path, use_container_width=True)
                    if image.caption:
                        st.caption(image.caption)
        
        st.write(f"**Category:** {service.category}")
        st.write(f"**Price per Night:** {service.price_rwf:,.0f} RWF")
        st.write(f"**Size:** {service.size}")
        st.write(f"**Max Capacity:** {service.max_capacity or 'N/A'} guests")
        
        st.subheader("Description")
        st.write(service.description)
        
        st.subheader("Details")
        st.write(service.details)
    
    with col2:
        # Booking form
        st.subheader("Book Now")
        if st.session_state.username:
            start_date = st.date_input("Check-in Date", min_value=date.today())
            end_date = st.date_input("Check-out Date", min_value=start_date)
            
            # Calculate number of nights
            nights = (end_date - start_date).days
            if nights < 1:
                st.error("Please select at least one night")
                return
            
            # Guest count with proper validation
            max_guests = service.max_capacity if service.max_capacity is not None else 1
            guest_count = st.number_input(
                "Number of Guests",
                min_value=1,
                max_value=max_guests,
                value=1,
                help=f"Maximum {max_guests} guests allowed"
            )
            
            special_requests = st.text_area("Special Requests")
            
            # Calculate and display price breakdown
            price_per_night = service.price_rwf
            total_price = price_per_night * nights
            
            st.write("**Price Breakdown:**")
            st.write(f"Price per night: {price_per_night:,.0f} RWF")
            st.write(f"Number of nights: {nights}")
            st.write(f"**Total Price:** {total_price:,.0f} RWF")
            
            if st.button("Book Now"):
                if guest_count > max_guests:
                    st.error(f"Maximum {max_guests} guests allowed for this service.")
                    return
                
                user = session.execute(
                    select(User).where(User.username == st.session_state.username)
                ).scalar_one_or_none()
                
                if user:
                    booking = Booking(
                        user_id=user.user_id,
                        service_id=service.service_id,
                        start_date=start_date,
                        end_date=end_date,
                        total_price_rwf=total_price,
                        guest_count=guest_count,
                        special_requests=special_requests,
                        booking_status="pending"
                    )
                    session.add(booking)
                    session.commit()
                    st.success("Booking request submitted successfully!")
        else:
            st.warning("Please log in to book this service.")

def package_details_page(package_id):
    # Back button
    if st.button("← Back to Packages"):
        del st.session_state.selected_package
        st.rerun()
    
    package = session.get(Package, package_id)
    if not package:
        st.error("Package not found!")
        return
    
    # Main content in horizontal layout
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.title(package.name)
        
        # Display cover image
        if package.cover_image:
            st.image(package.cover_image, use_container_width=True)
        
        st.write(f"**Category:** {package.category}")
        st.write(f"**Base Price:** {package.base_price_rwf:,.0f} RWF")
        st.write(f"**Duration:** {package.duration_days} day{'s' if package.duration_days > 1 else ''}")
        st.write(f"**Max Guests:** {package.max_guests}")
        
        st.subheader("Description")
        st.write(package.description)
        
        # Services in horizontal grid
        st.subheader("Included Services")
        service_cols = st.columns(3)
        for idx, service in enumerate(package.services):
            with service_cols[idx % 3]:
                if service.cover_image:
                    st.image(service.cover_image, use_container_width=True)
                    st.markdown(f"""
                    <div class="service-card">
                        <h4>{service.name}</h4>
                        <p>{service.description}</p>
                        <p><strong>Value:</strong> {service.price_rwf:,.0f} RWF</p>
                    </div>
                    """, unsafe_allow_html=True)
    
    with col2:
        # Booking form
        st.subheader("Book Package")
        if st.session_state.username:
            start_date = st.date_input("Start Date", min_value=date.today())
            end_date = start_date + timedelta(days=package.duration_days)
            st.write(f"End Date: {end_date}")
            
            # Guest count with proper validation
            guest_count = st.number_input(
                "Number of Guests",
                min_value=1,
                max_value=package.max_guests,
                value=1,
                help=f"Maximum {package.max_guests} guests allowed"
            )
            
            special_requests = st.text_area("Special Requests")
            
            # Customizable add-ons if package is customizable
            selected_services = list(package.services)
            if package.is_customizable:
                st.subheader("Additional Services")
                add_on_services = session.execute(
                    select(Service).where(
                        Service.is_add_on == True,
                        ~Service.service_id.in_([s.service_id for s in package.services])
                    )
                ).scalars().all()
                
                # Display add-ons in a grid
                if add_on_services:
                    addon_cols = st.columns(2)
                    for idx, service in enumerate(add_on_services):
                        with addon_cols[idx % 2]:
                            if service.cover_image:
                                st.image(service.cover_image, use_container_width=True)
                            if st.checkbox(f"Add {service.name} (+{service.price_rwf:,.0f} RWF)"):
                                selected_services.append(service)
            
            # Calculate total price
            total_price = package.base_price_rwf
            for service in selected_services:
                if service not in package.services:  # Only add price for additional services
                    if service.category == "Add-on":
                        total_price += service.price_rwf * guest_count
                    else:
                        total_price += service.price_rwf
            
            st.write(f"**Total Price:** {total_price:,.0f} RWF")
            
            if st.button("Book Package"):
                if guest_count > package.max_guests:
                    st.error(f"Maximum {package.max_guests} guests allowed for this package.")
                    return
                
                user = session.execute(
                    select(User).where(User.username == st.session_state.username)
                ).scalar_one_or_none()
                
                if user:
                    booking = PackageBooking(
                        user_id=user.user_id,
                        package_id=package.package_id,
                        start_date=start_date,
                        end_date=end_date,
                        total_price_rwf=total_price,
                        guest_count=guest_count,
                        special_requests=special_requests,
                        selected_services=json.dumps([s.service_id for s in selected_services]),
                        booking_status="pending"
                    )
                    session.add(booking)
                    session.commit()
                    st.success("Package booking request submitted successfully!")
        else:
            st.warning("Please log in to book this package.")

# Update the main application logic
if st.session_state.authentication_status:
    st.sidebar.title("Navigation")
    if st.sidebar.button("Logout"):
        logout()

    if st.session_state.role == "Admin":
        page = st.sidebar.radio(
            "Go to", ["Home", "Packages", "Booking History", "Manage Users", "Manage Services", "Manage Packages"]
        )
    else:
        page = st.sidebar.radio("Go to", ["Home", "Packages", "Booking History"])

    if page == "Home":
        if hasattr(st.session_state, 'selected_service'):
            service_details_page(st.session_state.selected_service)
        else:
            home_page()
    elif page == "Packages":
        if hasattr(st.session_state, 'selected_package'):
            package_details_page(st.session_state.selected_package)
        else:
            packages_page()
    elif page == "Booking History":
        booking_history_page()
    elif page == "Manage Users":
        user_management_page()
    elif page == "Manage Services":
        service_management_page()
    elif page == "Manage Packages":
        package_management_page()
else:
    login() 