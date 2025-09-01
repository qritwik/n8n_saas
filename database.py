import sqlite3
from typing import Optional, Dict, List
import hashlib


class UserDB:
    def __init__(self, db_path: str = "users.db"):
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        """Create user tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # User accounts table for login/register
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_accounts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT,
                    password_hash TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )
            """
            )
            
            # Credentials table for Gmail OAuth tokens
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS credentials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    n8n_credential_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES user_accounts (id)
                )
            """
            )
            
            # Workflows table for n8n workflows
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    credential_id INTEGER NOT NULL,
                    n8n_workflow_id TEXT UNIQUE,
                    workflow_name TEXT DEFAULT 'Gmail to Telegram Automation',
                    workflow_status TEXT DEFAULT 'inactive',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active',
                    FOREIGN KEY (user_id) REFERENCES user_accounts (id),
                    FOREIGN KEY (credential_id) REFERENCES credentials (id)
                )
            """
            )
            conn.commit()

    def create_user(self, username: str, password: str, email: str = None) -> bool:
        """Create a new user account"""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO user_accounts (username, email, password_hash)
                    VALUES (?, ?, ?)
                """,
                    (username, email, password_hash),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            return False  # Username already exists

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM user_accounts 
                WHERE username = ? AND password_hash = ? AND status = 'active'
            """,
                (username, password_hash),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_accounts WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def save_credential(self, user_id: int, email: str, access_token: str, refresh_token: str) -> int:
        """Save or update Gmail credential and return credential ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO credentials (user_id, email, access_token, refresh_token)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    user_id = excluded.user_id,
                    access_token = excluded.access_token,
                    refresh_token = excluded.refresh_token,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """,
                (user_id, email, access_token, refresh_token),
            )
            credential_id = cursor.fetchone()[0]
            conn.commit()
            return credential_id

    def update_credential_n8n_id(self, credential_id: int, n8n_credential_id: str) -> None:
        """Update credential with n8n credential ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE credentials 
                SET n8n_credential_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (n8n_credential_id, credential_id),
            )
            conn.commit()

    def create_workflow(self, user_id: int, credential_id: int, n8n_workflow_id: str, workflow_name: str = "Gmail to Telegram Automation") -> int:
        """Create a new workflow record"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO workflows (user_id, credential_id, n8n_workflow_id, workflow_name)
                VALUES (?, ?, ?, ?)
                RETURNING id
            """,
                (user_id, credential_id, n8n_workflow_id, workflow_name),
            )
            workflow_id = cursor.fetchone()[0]
            conn.commit()
            return workflow_id

    def update_workflow_status(self, workflow_id: int, status: str) -> None:
        """Update workflow status"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE workflows 
                SET workflow_status = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (status, workflow_id),
            )
            conn.commit()

    def get_user_credential(self, user_id: int) -> Optional[Dict]:
        """Get user's Gmail credential"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM credentials 
                WHERE user_id = ? AND status = 'active'
                ORDER BY updated_at DESC
                LIMIT 1
            """,
                (user_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_workflow(self, user_id: int) -> Optional[Dict]:
        """Get user's workflow"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.*, c.email as gmail_email 
                FROM workflows w
                JOIN credentials c ON w.credential_id = c.id
                WHERE w.user_id = ? AND w.status = 'active'
                ORDER BY w.updated_at DESC
                LIMIT 1
            """,
                (user_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_user_dashboard_data(self, user_id: int) -> Dict:
        """Get all data needed for user dashboard"""
        credential = self.get_user_credential(user_id)
        workflow = self.get_user_workflow(user_id)
        
        return {
            'credential': credential,
            'workflow': workflow
        }

    def get_credential_by_email(self, email: str) -> Optional[Dict]:
        """Get credential by email"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM credentials WHERE email = ? AND status = 'active'", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_workflow_by_n8n_id(self, n8n_workflow_id: str) -> Optional[Dict]:
        """Get workflow by n8n workflow ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.*, c.email as gmail_email, ua.username
                FROM workflows w
                JOIN credentials c ON w.credential_id = c.id
                JOIN user_accounts ua ON w.user_id = ua.id
                WHERE w.n8n_workflow_id = ? AND w.status = 'active'
            """,
                (n8n_workflow_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_workflows(self) -> List[Dict]:
        """Get all workflows with user and credential info"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT w.*, c.email as gmail_email, ua.username, ua.email as user_email
                FROM workflows w
                JOIN credentials c ON w.credential_id = c.id
                JOIN user_accounts ua ON w.user_id = ua.id
                WHERE w.status = 'active'
                ORDER BY w.created_at DESC
            """
            )
            return [dict(row) for row in cursor.fetchall()]

    def delete_user_credential(self, user_id: int) -> bool:
        """Delete user's credential"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM credentials WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_user_workflow(self, user_id: int) -> bool:
        """Delete user's workflow"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM workflows WHERE user_id = ?", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_workflow_by_n8n_id(self, n8n_workflow_id: str) -> bool:
        """Delete workflow by n8n workflow ID"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM workflows WHERE n8n_workflow_id = ?", (n8n_workflow_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_credential_by_email(self, email: str) -> bool:
        """Delete credential by email"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM credentials WHERE email = ?", (email,))
            conn.commit()
            return cursor.rowcount > 0

    # Legacy methods for backward compatibility
    def save_user(self, email: str, access_token: str, refresh_token: str) -> None:
        """Legacy method - use save_credential instead"""
        pass

    def get_user(self, email: str) -> Optional[Dict]:
        """Legacy method - use get_credential_by_email instead"""
        return self.get_credential_by_email(email)

    def get_all_users(self) -> List[Dict]:
        """Legacy method - use get_all_workflows instead"""
        return self.get_all_workflows()

    def delete_user(self, email: str) -> bool:
        """Legacy method - use delete_credential_by_email instead"""
        return self.delete_credential_by_email(email)

    def save_gmail_connection(self, user_id: int, email: str, access_token: str, refresh_token: str) -> None:
        """Legacy method - use save_credential instead"""
        self.save_credential(user_id, email, access_token, refresh_token)

    def get_user_gmail_connection(self, user_id: int) -> Optional[Dict]:
        """Legacy method - use get_user_credential instead"""
        return self.get_user_credential(user_id)

    def update_workflow_info(self, email: str, credential_id: str, workflow_id: str, workflow_status: str = "active") -> None:
        """Legacy method - use create_workflow and update_workflow_status instead"""
        pass
