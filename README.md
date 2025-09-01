# Gmail to Telegram Automation SaaS

A Flask-based SaaS application that automates Gmail to Telegram notifications using n8n workflows.

## Features

### 🔐 User Authentication
- **User Registration**: Create accounts with username, email, and password
- **User Login**: Secure authentication system
- **Session Management**: Persistent login sessions
- **Password Security**: SHA-256 hashed passwords

### 📧 Gmail Integration
- **OAuth 2.0 Authentication**: Secure Gmail API access
- **Credential Management**: Store and manage Gmail credentials
- **Duplicate Prevention**: Prevent multiple users from connecting the same Gmail account
- **Automatic Token Refresh**: Handle OAuth token expiration

### 🔄 Workflow Management
- **Automatic Workflow Creation**: Generate n8n workflows automatically
- **Workflow Status Tracking**: Monitor workflow status (active/inactive)
- **Workflow Viewing**: Direct links to n8n workflow interface
- **Workflow Recreation**: Create workflows for existing Gmail connections

### 📊 Dashboard
- **Real-time Status**: View Gmail connection and workflow status
- **Workflow Information**: Display workflow IDs, status, and creation dates
- **Quick Actions**: Connect Gmail, create workflows, disconnect accounts
- **User Management**: Admin view of all users and workflows

## Database Schema

The application uses a normalized database structure with separate tables:

### `user_accounts`
- User authentication and profile information
- Username, email, password hash, creation date

### `credentials`
- Gmail OAuth credentials
- Access tokens, refresh tokens, n8n credential IDs
- Linked to user accounts via foreign key

### `workflows`
- n8n workflow information
- Workflow IDs, status, creation dates
- Linked to both users and credentials

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd n8n_saas
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   - Set up Google OAuth credentials
   - Configure n8n API settings
   - Update `config.py` with your settings

4. **Run database migration** (if upgrading from old version)
   ```bash
   python migrate_db.py
   ```

5. **Start the application**
   ```bash
   python app.py
   ```

## Usage

### For Users

1. **Register/Login**: Create an account or login to existing account
2. **Connect Gmail**: Authorize Gmail access through OAuth
3. **Create Workflow**: Automatically generate n8n workflow
4. **Monitor**: View workflow status and manage connections

### For Administrators

1. **User Management**: View all users and their workflows
2. **Workflow Monitoring**: Track workflow status across all users
3. **Troubleshooting**: Access individual workflow details

## API Endpoints

### Authentication
- `GET/POST /login` - User login
- `GET/POST /register` - User registration
- `GET /logout` - User logout

### Dashboard
- `GET /dashboard` - User dashboard (requires login)
- `GET /auth` - Initiate Gmail OAuth
- `GET /login/callback` - OAuth callback handler
- `GET /create-workflow` - Create workflow for existing Gmail connection
- `POST /disconnect-gmail` - Disconnect Gmail account

### Management
- `GET /users` - View all users (admin)
- `POST /users/<email>/delete` - Delete user workflow
- `GET /workflow/<id>` - View specific workflow

### API
- `GET /api/users` - JSON API for user data
- `GET /api/health` - Health check endpoint

## Security Features

- **Password Hashing**: SHA-256 password encryption
- **Session Management**: Secure session handling
- **OAuth 2.0**: Secure Gmail API authentication
- **Input Validation**: Form validation and sanitization
- **SQL Injection Prevention**: Parameterized queries
- **CSRF Protection**: Form-based CSRF protection

## Configuration

Update `config.py` with your settings:

```python
# Google OAuth
GOOGLE_CLIENT_ID = "your_client_id"
GOOGLE_CLIENT_SECRET = "your_client_secret"
GOOGLE_REDIRECT_URI = "http://localhost:5000/login/callback"

# n8n Configuration
N8N_API_KEY = "your_n8n_api_key"
N8N_BASE_URL = "http://localhost:5678"
```

## Database Migration

If upgrading from the old single-table schema, run the migration script:

```bash
python migrate_db.py
```

This will:
- Preserve existing Gmail connections
- Create user accounts for existing connections
- Migrate workflow data to new schema
- Set temporary passwords for migrated users

**Important**: Users with temporary passwords should reset them after migration.

## Development

### Project Structure
```
n8n_saas/
├── app.py              # Main Flask application
├── database.py         # Database models and operations
├── n8n_manager.py      # n8n API integration
├── oauth_handler.py    # Google OAuth handling
├── config.py           # Configuration settings
├── migrate_db.py       # Database migration script
├── requirements.txt    # Python dependencies
├── templates/          # HTML templates
│   ├── index.html      # Landing page
│   ├── login.html      # Login page
│   ├── register.html   # Registration page
│   ├── dashboard.html  # User dashboard
│   ├── users.html      # Admin user list
│   ├── success.html    # Success page
│   └── error.html      # Error page
└── users.db           # SQLite database
```

### Adding New Features

1. **Database Changes**: Update `database.py` with new tables/methods
2. **Routes**: Add new routes in `app.py`
3. **Templates**: Create new HTML templates
4. **Migration**: Update migration script if needed

## Troubleshooting

### Common Issues

1. **OAuth Errors**: Check Google OAuth configuration
2. **Database Errors**: Run migration script for schema updates
3. **n8n Connection**: Verify n8n API key and base URL
4. **Session Issues**: Clear browser cookies and restart application

### Logs

The application provides detailed console logging for debugging:
- OAuth flow steps
- Database operations
- n8n API calls
- Error messages

## License

This project is licensed under the MIT License.
