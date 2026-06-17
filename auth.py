
import sqlite3
import hashlib
from typing import Optional, Tuple, List, Dict, Any
from datetime import datetime

class AuthManager:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize database with users table"""
        with sqlite3.connect(self.db_path) as conn:
            # Users table with additional fields
            conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    telegram_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_login TIMESTAMP,
                    role TEXT DEFAULT 'user'
                )
            ''')
            
            # Create admin user if not exists
            cursor = conn.execute("SELECT username FROM users WHERE username = 'admin'")
            if not cursor.fetchone():
                admin_hash = hashlib.sha256("admin123".encode()).hexdigest()
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                    ("admin", admin_hash, "admin")
                )
            
            conn.commit()

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username: str, password: str) -> bool:
        """Register a new user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, self._hash_password(password))
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def login(self, username: str, password: str) -> bool:
        """Login user and update last login time"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            if row and row[0] == self._hash_password(password):
                # Update last login time
                conn.execute(
                    "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE username = ?",
                    (username,)
                )
                conn.commit()
                return True
        return False

    def update_telegram(self, username: str, telegram_id: str):
        """Update user's Telegram ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "UPDATE users SET telegram_id = ? WHERE username = ?",
                (telegram_id, username)
            )
            conn.commit()

    def get_telegram_id(self, username: str) -> Optional[str]:
        """Get user's Telegram ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT telegram_id FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def get_all_users(self) -> List[Dict[str, Any]]:
        """Get all users with detailed information (Admin function)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    id,
                    username,
                    telegram_id,
                    created_at,
                    last_login,
                    role
                FROM users
                ORDER BY created_at DESC
            """)
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    "id": row[0],
                    "username": row[1],
                    "telegram_id": row[2] or "Not set",
                    "created_at": row[3],
                    "last_login": row[4] or "Never",
                    "role": row[5]
                })
            return users

    def get_user_role(self, username: str) -> str:
        """Get user's role"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT role FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            return row[0] if row else "user"

    def get_user_stats(self) -> Dict[str, Any]:
        """Get statistics about users"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN telegram_id IS NOT NULL THEN 1 END) as users_with_telegram,
                    COUNT(CASE WHEN role = 'admin' THEN 1 END) as admin_users,
                    COUNT(CASE WHEN last_login IS NOT NULL THEN 1 END) as active_users
                FROM users
            """)
            row = cursor.fetchone()
            
            return {
                "total_users": row[0],
                "users_with_telegram": row[1],
                "admin_users": row[2],
                "active_users": row[3]
            }

    def delete_user(self, username: str) -> bool:
        """Delete a user (Admin function)"""
        if username == "admin":
            return False  # Prevent deleting admin
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "DELETE FROM users WHERE username = ?",
                    (username,)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            return False

    def update_user_role(self, username: str, role: str) -> bool:
        """Update user's role (Admin function)"""
        if username == "admin" and role != "admin":
            return False  # Prevent removing admin role from admin user
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE users SET role = ? WHERE username = ?",
                    (role, username)
                )
                conn.commit()
                return True
        except Exception as e:
            print(f"Error updating user role: {e}")
            return False

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user details by ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    id,
                    username,
                    telegram_id,
                    created_at,
                    last_login,
                    role
                FROM users
                WHERE id = ?
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "username": row[1],
                    "telegram_id": row[2],
                    "created_at": row[3],
                    "last_login": row[4],
                    "role": row[5]
                }
            return None

    def search_users(self, search_term: str) -> List[Dict[str, Any]]:
        """Search users by username"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    id,
                    username,
                    telegram_id,
                    created_at,
                    last_login,
                    role
                FROM users
                WHERE username LIKE ?
                ORDER BY username
            """, (f"%{search_term}%",))
            
            users = []
            for row in cursor.fetchall():
                users.append({
                    "id": row[0],
                    "username": row[1],
                    "telegram_id": row[2] or "Not set",
                    "created_at": row[3],
                    "last_login": row[4] or "Never",
                    "role": row[5]
                })
            return users
