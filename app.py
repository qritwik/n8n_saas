from flask import Flask, request, redirect, render_template, jsonify, session, flash, url_for
from database import UserDB
from oauth_handler import GoogleOAuth
from n8n_manager import N8NManager
import config
from functools import wraps

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Initialize components
db = UserDB()
oauth = GoogleOAuth()
n8n = N8NManager()


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route("/")
def home():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        
        if not username or not password:
            return render_template("login.html", error="Please provide both username and password")
        
        user = db.authenticate_user(username, password)
        if user:
            session['user_id'] = user['id']
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        else:
            return render_template("login.html", error="Invalid username or password")
    
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        # Validation
        if not all([username, password, confirm_password]):
            return render_template("register.html", error="All fields are required")
        
        if password != confirm_password:
            return render_template("register.html", error="Passwords do not match")
        
        if len(password) < 6:
            return render_template("register.html", error="Password must be at least 6 characters long")
        
        if len(username) < 3:
            return render_template("register.html", error="Username must be at least 3 characters long")
        
        # Create user
        if db.create_user(username, password):
            return render_template("login.html", success="Account created successfully! Please login.")
        else:
            return render_template("register.html", error="Username already exists")
    
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('home'))


@app.route("/dashboard")
@login_required
def dashboard():
    user_id = session['user_id']
    user = db.get_user_by_id(user_id)
    dashboard_data = db.get_user_dashboard_data(user_id)
    
    return render_template("dashboard.html", 
                         user=user, 
                         gmail_connection=dashboard_data['credential'],
                         workflow=dashboard_data['workflow'])


@app.route("/auth")
@login_required
def auth():
    return redirect(oauth.get_auth_url())


@app.route("/login/callback")
@login_required
def callback():
    """Handle OAuth callback and create workflow"""
    code = request.args.get("code")
    error = request.args.get("error")
    user_id = session['user_id']

    if error:
        flash(f"Authorization error: {error}", "error")
        return redirect(url_for('dashboard'))

    if not code:
        flash("No authorization code received", "error")
        return redirect(url_for('dashboard'))

    try:
        print("🔄 Processing OAuth callback...")

        # Exchange code for tokens
        tokens = oauth.exchange_code(code)
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        print("✅ Got OAuth tokens")

        # Get user email
        email = oauth.get_user_email(access_token)
        print(f"✅ User email: {email}")

        # Check if this Gmail account is already connected by another user
        existing_credential = db.get_credential_by_email(email)
        if existing_credential and existing_credential['user_id'] != user_id:
            flash(f"Gmail account {email} is already connected by another user", "error")
            return redirect(url_for('dashboard'))

        # Save credential to database
        credential_id = db.save_credential(user_id, email, access_token, refresh_token)
        print("✅ Saved credential to database")

        # Create n8n credential
        print("🔄 Creating n8n credential...")
        n8n_credential = n8n.create_credential(email, access_token, refresh_token)
        n8n_credential_id = n8n_credential["id"]
        print(f"✅ Created n8n credential: {n8n_credential_id}")

        # Update credential with n8n credential ID
        db.update_credential_n8n_id(credential_id, n8n_credential_id)

        # Create n8n workflow
        print("🔄 Creating n8n workflow...")
        workflow = n8n.create_or_update_workflow(email, n8n_credential_id)
        n8n_workflow_id = workflow["id"]
        print(f"✅ Created n8n workflow: {n8n_workflow_id}")

        # Save workflow to database
        workflow_id = db.create_workflow(user_id, credential_id, n8n_workflow_id)
        db.update_workflow_status(workflow_id, "active")
        print("✅ Saved workflow to database")

        flash(f"Successfully connected Gmail account {email} and created workflow!", "success")
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        flash(f"Setup failed: {str(e)}", "error")
        return redirect(url_for('dashboard'))


@app.route("/create-workflow")
@login_required
def create_workflow():
    """Create workflow for existing Gmail connection"""
    user_id = session['user_id']
    
    try:
        # Get user's credential
        credential = db.get_user_credential(user_id)
        if not credential:
            flash("No Gmail account connected. Please connect Gmail first.", "error")
            return redirect(url_for('dashboard'))

        # Check if workflow already exists
        existing_workflow = db.get_user_workflow(user_id)
        if existing_workflow:
            flash("Workflow already exists for this account.", "error")
            return redirect(url_for('dashboard'))

        # Create n8n workflow
        print("🔄 Creating n8n workflow...")
        workflow = n8n.create_or_update_workflow(credential['email'], credential['n8n_credential_id'])
        n8n_workflow_id = workflow["id"]
        print(f"✅ Created n8n workflow: {n8n_workflow_id}")

        # Save workflow to database
        workflow_id = db.create_workflow(user_id, credential['id'], n8n_workflow_id)
        db.update_workflow_status(workflow_id, "active")
        print("✅ Saved workflow to database")

        flash("Workflow created successfully!", "success")
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"❌ Workflow creation failed: {str(e)}")
        flash(f"Workflow creation failed: {str(e)}", "error")
        return redirect(url_for('dashboard'))


@app.route("/disconnect-gmail", methods=["POST"])
@login_required
def disconnect_gmail():
    """Disconnect Gmail account and delete workflow"""
    user_id = session['user_id']
    
    try:
        # Get user's data
        credential = db.get_user_credential(user_id)
        workflow = db.get_user_workflow(user_id)
        
        if not credential:
            flash("No Gmail account connected.", "error")
            return redirect(url_for('dashboard'))

        # Delete n8n workflow if exists
        if workflow and workflow['n8n_workflow_id']:
            n8n.delete_workflow(workflow['n8n_workflow_id'])
            print(f"✅ Deleted n8n workflow: {workflow['n8n_workflow_id']}")

        # Delete n8n credential if exists
        if credential['n8n_credential_id']:
            n8n.delete_credential(credential['n8n_credential_id'])
            print(f"✅ Deleted n8n credential: {credential['n8n_credential_id']}")

        # Delete from database
        db.delete_user_workflow(user_id)
        db.delete_user_credential(user_id)
        print(f"✅ Deleted user data from database")

        flash("Gmail account disconnected successfully!", "success")
        return redirect(url_for('dashboard'))

    except Exception as e:
        print(f"❌ Disconnect failed: {str(e)}")
        flash(f"Disconnect failed: {str(e)}", "error")
        return redirect(url_for('dashboard'))


@app.route("/workflow/<workflow_id>")
@login_required
def view_workflow(workflow_id):
    """Redirect to n8n workflow"""
    user_id = session['user_id']
    
    # Verify user owns this workflow
    workflow = db.get_workflow_by_n8n_id(workflow_id)
    if not workflow or workflow['user_id'] != user_id:
        flash("Workflow not found or access denied.", "error")
        return redirect(url_for('dashboard'))
    
    # Redirect to n8n workflow
    n8n_url = f"{n8n.base_url}/workflow/{workflow_id}"
    return redirect(n8n_url)


@app.route("/users")
@login_required
def show_users():
    users = db.get_all_workflows()
    return render_template("users.html", users=users)


@app.route("/users/<email>/delete", methods=["POST"])
@login_required
def delete_user(email):
    try:
        credential = db.get_credential_by_email(email)
        if not credential:
            flash("User not found", "error")
            return redirect(url_for('show_users'))

        # Get workflow for this credential
        workflow = db.get_user_workflow(credential['user_id'])

        if workflow and workflow['n8n_workflow_id']:
            n8n.delete_workflow(workflow['n8n_workflow_id'])
            print(f"✅ Deleted workflow: {workflow['n8n_workflow_id']}")

        if credential['n8n_credential_id']:
            n8n.delete_credential(credential['n8n_credential_id'])
            print(f"✅ Deleted credential: {credential['n8n_credential_id']}")

        db.delete_user_credential(credential['user_id'])
        print(f"✅ Deleted user: {email}")

        flash(f"User {email} deleted successfully", "success")
        return redirect(url_for('show_users'))

    except Exception as e:
        print(f"❌ Delete failed: {str(e)}")
        flash(f"Delete failed: {str(e)}", "error")
        return redirect(url_for('show_users'))


@app.route("/api/users")
def api_users():
    users = db.get_all_workflows()
    return jsonify(users)


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "gmail-telegram-automation"})


if __name__ == "__main__":
    print("🚀 Starting Gmail to Telegram automation server...")
    print(f"📡 n8n URL: {n8n.base_url}")
    print(f"🔑 Using API key: {config.N8N_API_KEY[:20]}...")
    app.run(debug=True, port=5000, host="0.0.0.0", ssl_context="adhoc")
