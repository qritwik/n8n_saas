from flask import Flask, request, redirect, render_template, jsonify
from database import UserDB
from oauth_handler import GoogleOAuth
from n8n_manager import N8NManager
import config

app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# Initialize components
db = UserDB()
oauth = GoogleOAuth()
n8n = N8NManager()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/auth")
def auth():
    return redirect(oauth.get_auth_url())


@app.route("/login/callback")
def callback():
    """Handle OAuth callback and create workflow"""
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        return render_template("error.html", error=f"Authorization error: {error}")

    if not code:
        return render_template("error.html", error="No authorization code received")

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

        # Save user to database
        db.save_user(email, access_token, refresh_token)
        print("✅ Saved user to database")

        # Create n8n credential
        print("🔄 Creating n8n credential...")
        credential = n8n.create_credential(email, access_token, refresh_token)
        credential_id = credential["id"]
        print(f"✅ Created n8n credential: {credential_id}")

        # Create n8n workflow
        print("🔄 Creating n8n workflow...")
        workflow = n8n.create_or_update_workflow(email, credential_id)
        workflow_id = workflow["id"]
        print(f"✅ Created n8n workflow: {workflow_id}")

        # Update user with workflow info
        db.update_workflow_info(email, credential_id, workflow_id)
        print("✅ Updated user record")

        return render_template("success.html", email=email, workflow_id=workflow_id)

    except Exception as e:
        print(f"❌ Setup failed: {str(e)}")
        return render_template("error.html", error=f"Setup failed: {str(e)}")


@app.route("/users")
def show_users():
    users = db.get_all_users()
    return render_template("users.html", users=users)


@app.route("/users/<email>/delete", methods=["POST"])
def delete_user(email):
    try:
        user = db.get_user(email)
        if not user:
            return render_template("error.html", error="User not found")

        if user["workflow_id"]:
            n8n.delete_workflow(user["workflow_id"])
            print(f"✅ Deleted workflow: {user['workflow_id']}")

        if user["credential_id"]:
            n8n.delete_credential(user["credential_id"])
            print(f"✅ Deleted credential: {user['credential_id']}")

        db.delete_user(email)
        print(f"✅ Deleted user: {email}")

        return redirect("/users")

    except Exception as e:
        print(f"❌ Delete failed: {str(e)}")
        return render_template("error.html", error=f"Delete failed: {str(e)}")


@app.route("/api/users")
def api_users():
    users = db.get_all_users()
    return jsonify(users)


@app.route("/api/health")
def health():
    return jsonify({"status": "healthy", "service": "gmail-telegram-automation"})


if __name__ == "__main__":
    print("🚀 Starting Gmail to Telegram automation server...")
    print(f"📡 n8n URL: {n8n.base_url}")
    print(f"🔑 Using API key: {config.N8N_API_KEY[:20]}...")
    app.run(debug=True, port=5000, host="0.0.0.0", ssl_context="adhoc")
