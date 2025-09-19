# auth_helper.py
from flask import Flask, render_template_string
import os
import sys
from dotenv import load_dotenv

# Load environment variables from firebase.env
load_dotenv(dotenv_path='firebase.env')

# Build the config dictionary from environment variables
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID")
}

# Check if the configuration was loaded successfully
if not FIREBASE_CONFIG["apiKey"]:
    print("FATAL ERROR: Firebase configuration not found in auth_helper.py.")
    print("Please ensure your 'firebase.env' file is correct and in the same folder.")
    sys.exit(1)

# --- FIX: Initialize the Flask app ---
app = Flask(__name__)

# Simple HTML page with Firebase JS to handle login
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>EmpathicBot Login</title>
    <style>
        body { font-family: sans-serif; display: flex; flex-direction: column; align-items: center; padding-top: 50px; background-color: #f4f4f9; }
        #container { background: white; padding: 40px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; }
        h1 { color: #333; }
        button { background-color: #4285F4; color: white; border: none; padding: 12px 20px; border-radius: 4px; font-size: 16px; cursor: pointer; transition: background-color 0.3s; }
        button:hover { background-color: #357ae8; }
        textarea { width: 100%; box-sizing: border-box; height: 150px; margin-top: 20px; font-family: monospace; font-size: 12px; padding: 10px; border: 1px solid #ccc; border-radius: 4px; }
    </style>
</head>
<body>
    <div id="container">
        <h1>EmpathicBot Authentication</h1>
        <p>Sign in with Google to get your ID Token for the CLI.</p>
        <button onclick="signInWithGoogle()">Sign in with Google</button>
        <div id="token-display" style="display:none;">
            <h3>Your ID Token (copy this and paste it into your terminal):</h3>
            <textarea id="id-token" readonly onclick="this.select()"></textarea>
        </div>
    </div>

    <script src="https://www.gstatic.com/firebasejs/9.6.1/firebase-app-compat.js"></script>
    <script src="https://www.gstatic.com/firebasejs/9.6.1/firebase-auth-compat.js"></script>
    <script>
        const firebaseConfig = {{ firebase_config | tojson }};
        firebase.initializeApp(firebaseConfig);
        const auth = firebase.auth();

        async function signInWithGoogle() {
            const provider = new firebase.auth.GoogleAuthProvider();
            try {
                const result = await auth.signInWithPopup(provider);
                const idToken = await result.user.getIdToken();
                document.getElementById('id-token').value = idToken;
                document.getElementById('token-display').style.display = 'block';
            } catch (error) {
                console.error("Authentication Error:", error);
                alert("Failed to sign in: " + error.message);
            }
        }
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, firebase_config=FIREBASE_CONFIG)

if __name__ == "__main__":
    print("Auth Helper running on http://127.0.0.1:5001")
    print("Open this URL in your browser to sign in with Google.")
    app.run(port=5001)