
#!/usr/bin/env python3
"""
Database initialization script for Intelligent Agent System.
Run this script once to set up the database.
"""

import sqlite3
import hashlib
import os

def init_database():
    """Initialize the SQLite database with users table"""
    
    # Database file path
    db_path = "users.db"
    
    # Remove existing database if exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print("Removed existing database.")
    
    # Create new database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            telegram_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            role TEXT DEFAULT 'user'
        )
    ''')
    
    # Create admin user
    admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
    cursor.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
        ("admin", admin_hash, "admin")
    )
    
    # Create some test users
    test_users = [
        ("john_doe", "password123"),
        ("jane_smith", "password456"),
        ("test_user", "test123"),
    ]
    
    for username, password in test_users:
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        cursor.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, password_hash)
        )
    
    # Commit changes
    conn.commit()
    
    # Display created users
    print("Database initialized successfully!")
    print("\nCreated users:")
    print("=" * 50)
    print(f"{'Username':<15} {'Password':<15} {'Role':<10}")
    print("-" * 50)
    print(f"{'admin':<15} {'admin123':<15} {'admin':<10}")
    for username, password in test_users:
        print(f"{username:<15} {password:<15} {'user':<10}")
    print("=" * 50)
    print(f"\nDatabase file: {os.path.abspath(db_path)}")
    
    # Close connection
    conn.close()

if __name__ == "__main__":
    print("Initializing Intelligent Agent System Database...")
    print("This will create a new database with default users.")
    print("Make sure to change the default passwords after setup!")
    print()
    
    confirm = input("Are you sure you want to continue? (yes/no): ")
    if confirm.lower() in ['yes', 'y']:
        init_database()
    else:
        print("Database initialization cancelled.")
