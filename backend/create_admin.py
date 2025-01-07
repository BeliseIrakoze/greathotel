import sqlite3
import bcrypt
import auth

def create_initial_admin():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE username='admin'")
    if c.fetchone() is None:
        print("Creating admin user...")
        auth.create_user('admin', 'admin', 'Admin')
        conn.close()
        print("Admin user created successfully.")
    else:
        conn.close()
        print("Admin user already exists.")
    conn.close()

if __name__ == "__main__":
    create_initial_admin()