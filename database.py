import psycopg2
import psycopg2.extras
from typing import Optional, Dict, List
import hashlib
from config import DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD


class UserDB:
    def __init__(self):
        self.conn_string = f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} user={DB_USER} password={DB_PASSWORD}"

    def _get_connection(self):
        return psycopg2.connect(self.conn_string)

    def create_user(self, username: str, password: str, email: str = None) -> bool:
        """Create a new user account"""
        try:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            with self._get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO user_accounts (username, email, password_hash)
                        VALUES (%s, %s, %s)
                    """,
                        (username, email, password_hash),
                    )
                conn.commit()
                return True
        except psycopg2.IntegrityError:
            return False  # Username already exists

    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """Authenticate user and return user data"""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM user_accounts 
                    WHERE username = %s AND password_hash = %s AND status = 'active'
                """,
                    (username, password_hash),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM user_accounts WHERE id = %s", (user_id,))
                row = cursor.fetchone()
                return dict(row) if row else None

    def save_credential(self, user_id: int, email: str, access_token: str, refresh_token: str) -> int:
        """Save or update Gmail credential and return credential ID"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO gmail_credentials (user_id, gmail_email, access_token, refresh_token)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (gmail_email) DO UPDATE SET
                        user_id = EXCLUDED.user_id,
                        access_token = EXCLUDED.access_token,
                        refresh_token = EXCLUDED.refresh_token,
                        updated_at = CURRENT_TIMESTAMP
                    RETURNING id
                """,
                    (user_id, email, access_token, refresh_token),
                )
                credential_id = cursor.fetchone()
            conn.commit()
            return credential_id

    def update_credential_n8n_id(self, credential_id: int, n8n_gmail_credential: str) -> None:
        """Update credential with n8n credential ID"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE gmail_credentials 
                    SET n8n_gmail_credential = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """,
                    (n8n_gmail_credential, credential_id),
                )
            conn.commit()

    def create_workflow(self, user_id: int, gmail_credential_id: int, n8n_workflow_id: str, workflow_name: str = "Gmail to Telegram Automation") -> int:
        """Create a new workflow record"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO workflows (user_id, gmail_credential_id, n8n_workflow_id, workflow_name)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """,
                    (user_id, gmail_credential_id, n8n_workflow_id, workflow_name),
                )
                workflow_id = cursor.fetchone()
            conn.commit()
            return workflow_id

    def update_workflow_status(self, workflow_id: int, status: str) -> None:
        """Update workflow status"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE workflows 
                    SET workflow_status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """,
                    (status, workflow_id),
                )
            conn.commit()

    def get_user_credential(self, user_id: int) -> Optional[Dict]:
        """Get user's Gmail credential"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT * FROM gmail_credentials 
                    WHERE user_id = %s AND status = 'active'
                    ORDER BY updated_at DESC
                    LIMIT 1
                """,
                    (user_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_user_workflow(self, user_id: int) -> Optional[Dict]:
        """Get user's workflow"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT w.*, c.gmail_email 
                    FROM workflows w
                    JOIN gmail_credentials c ON w.gmail_credential_id = c.id
                    WHERE w.user_id = %s AND w.status = 'active'
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
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT * FROM gmail_credentials WHERE gmail_email = %s AND status = 'active'", (email,))
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_workflow_by_n8n_id(self, n8n_workflow_id: str) -> Optional[Dict]:
        """Get workflow by n8n workflow ID"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT w.*, c.gmail_email, ua.username
                    FROM workflows w
                    JOIN gmail_credentials c ON w.gmail_credential_id = c.id
                    JOIN user_accounts ua ON w.user_id = ua.id
                    WHERE w.n8n_workflow_id = %s AND w.status = 'active'
                """,
                    (n8n_workflow_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def get_all_workflows(self) -> List[Dict]:
        """Get all workflows with user and credential info"""
        with self._get_connection() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT w.*, c.gmail_email, ua.username, ua.email as user_email
                    FROM workflows w
                    JOIN gmail_credentials c ON w.gmail_credential_id = c.id
                    JOIN user_accounts ua ON w.user_id = ua.id
                    WHERE w.status = 'active'
                    ORDER BY w.created_at DESC
                """
                )
                return [dict(row) for row in cursor.fetchall()]

    def delete_user_credential(self, user_id: int) -> bool:
        """Delete user's credential"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM gmail_credentials WHERE user_id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_user_workflow(self, user_id: int) -> bool:
        """Delete user's workflow"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM workflows WHERE user_id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_workflow_by_n8n_id(self, n8n_workflow_id: str) -> bool:
        """Delete workflow by n8n workflow ID"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM workflows WHERE n8n_workflow_id = %s", (n8n_workflow_id,))
            conn.commit()
            return cursor.rowcount > 0

    def delete_credential_by_email(self, email: str) -> bool:
        """Delete credential by email"""
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM gmail_credentials WHERE gmail_email = %s", (email,))
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
