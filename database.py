import sqlite3
from typing import Optional, Dict, List


class UserDB:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        """Create user tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    email TEXT PRIMARY KEY,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    credential_id TEXT,
                    workflow_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """
            )
            conn.commit()

    def save_user(self, email: str, access_token: str, refresh_token: str) -> None:
        """Save or update user tokens"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (email, access_token, refresh_token)
                VALUES (?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token
            """,
                (email, access_token, refresh_token),
            )
            conn.commit()

    def update_workflow_info(
        self, email: str, credential_id: str, workflow_id: str
    ) -> None:
        """Update user with n8n workflow info"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE users 
                SET credential_id = ?, workflow_id = ?
                WHERE email = ?
            """,
                (credential_id, workflow_id, email),
            )
            conn.commit()

    def get_user(self, email: str) -> Optional[Dict]:
        """Get user by email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_users(self) -> List[Dict]:
        """Get all users"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]

    def delete_user(self, email: str) -> bool:
        """Delete user from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE email = ?", (email,))
            conn.commit()
            return cursor.rowcount > 0
