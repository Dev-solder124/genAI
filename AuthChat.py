#!/usr/bin/env python3
"""
Interactive Chat Client for EmpathicBot with Firebase Authentication
Loads credentials securely from a firebase.env file.
"""
import requests
import json
import os
import sys
import time
import pyrebase
from dotenv import load_dotenv

# --- Load environment variables from firebase.env ---
load_dotenv(dotenv_path='firebase.env')

# --- Build the config dictionary from environment variables ---
FIREBASE_CONFIG = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "databaseURL": ""
}

# --- Check if the configuration was loaded successfully ---
if not FIREBASE_CONFIG["apiKey"]:
    print("FATAL ERROR: Firebase configuration not found.")
    print("Please ensure you have a 'firebase.env' file with your project credentials.")
    sys.exit(1)

CHATBOT_URL = "http://127.0.0.1:8080"

class AuthChatClient:
    def __init__(self):
        self.firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
        self.auth = self.firebase.auth()
        self.user_token = None
        self.user_profile = None
        self.session_id = None

    def sign_in_google(self):
        """Guides user through web-based Google Sign-in."""
        print("\n" + "="*50)
        print("🔑 Sign in with Google")
        print("="*50)
        print("1. Please run the auth helper web app in a separate terminal:")
        print("   python auth_helper.py")
        print("\n2. Open http://127.0.0.1:5001 in your browser and sign in.")
        print("3. Copy the ID Token provided on the web page.")

        token = input("\nPaste the ID Token here: ").strip()
        if not token:
            print("❌ Token cannot be empty.")
            return False

        # --- FIX: Verify token with backend to get profile ---
        try:
            headers = {"Authorization": f"Bearer {token}"}
            response = requests.post(f"{CHATBOT_URL}/login", headers=headers, timeout=10)

            if response.status_code == 200:
                self.user_token = token
                self.user_profile = response.json()
                display_name = self.user_profile.get("profile", {}).get("username", "Unknown")
                print(f"✅ Successfully authenticated as: {display_name}")
                return True
            else:
                print(f"❌ Authentication failed on backend: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Connection error during login: {e}")
            return False

    def sign_in_guest(self):
        """Signs in the user anonymously for a guest session."""
        print("\n" + "="*50)
        print("👤 Signing in as a Guest...")
        print("="*50)
        try:
            # Use Firebase REST API directly for anonymous auth since pyrebase4 doesn't support it properly
            import requests
            
            # Firebase REST API endpoint for anonymous sign-in
            firebase_api_key = FIREBASE_CONFIG["apiKey"]
            auth_url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={firebase_api_key}"
            
            # Request anonymous token
            auth_data = {
                "returnSecureToken": True
            }
            
            auth_response = requests.post(auth_url, json=auth_data, timeout=10)
            
            if auth_response.status_code == 200:
                auth_result = auth_response.json()
                self.user_token = auth_result['idToken']
                
                # First, test token verification
                headers = {"Authorization": f"Bearer {self.user_token}"}
                debug_response = requests.post(f"{CHATBOT_URL}/debug/token", headers=headers, timeout=10)
                
                if debug_response.status_code == 200:
                    debug_info = debug_response.json()
                    print(f"✅ Token verification successful. UID: {debug_info.get('uid', 'unknown')}")
                    
                    # Now, log in to our backend to get/create a profile
                    response = requests.post(f"{CHATBOT_URL}/login", headers=headers, timeout=10)

                    if response.status_code == 200:
                         self.user_profile = response.json()
                         print("✅ Successfully started a guest session.")
                         print("Note: Guest sessions don't persist between app restarts.")
                         return True
                    else:
                        print(f"❌ Guest session failed on backend: {response.text}")
                        return False
                else:
                    debug_info = debug_response.json()
                    print(f"❌ Token verification failed: {debug_info.get('error', 'Unknown error')}")
                    print(f"Error type: {debug_info.get('error_type', 'Unknown')}")
                    return False
            else:
                print(f"❌ Failed to get anonymous token: {auth_response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Could not start a guest session: {e}")
            return False

    def sign_out(self):
        self.user_token = None
        self.user_profile = None
        print("\n👋 You have been signed out.")

    def send_message(self, message):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.user_token}"
        }
        webhook_data = {
            "session": f"projects/genai-bot-kdf/agent/sessions/{self.session_id}",
            "messages": [{"text": {"text": [message]}}],
        }
        try:
            response = requests.post(f"{CHATBOT_URL}/dialogflow-webhook", json=webhook_data, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                return data.get("fulfillment_response", {}).get("messages", [{}])[0].get("text", {}).get("text", [""])[0]
            else:
                return f"Error: Server returned {response.status_code} - {response.text}"
        except Exception as e:
            return f"❌ Connection Error: {e}"

    def set_consent(self, consent_bool):
        """Set user consent via API call"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.user_token}"
        }
        try:
            response = requests.post(f"{CHATBOT_URL}/consent", json={"consent": consent_bool}, headers=headers, timeout=10)
            if response.status_code == 200:
                # Update local profile
                if 'profile' not in self.user_profile:
                    self.user_profile['profile'] = {}
                self.user_profile['profile']['consent'] = consent_bool
                return True
            else:
                print(f"❌ Error setting consent: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Connection error setting consent: {e}")
            return False

    def handle_consent_flow(self):
        """Handle the initial consent flow"""
        print("\n" + "="*50)
        print("🤖 Privacy & Memory Settings")
        print("="*50)
        print("EmpathicBot can remember important parts of our conversations")
        print("to provide better, more personalized support over time.")
        print("\nThis helps me:")
        print("• Remember your preferences and goals")
        print("• Avoid repeating the same questions")
        print("• Provide more contextual support")
        print("\nYour privacy matters:")
        print("• Only significant conversations are saved")
        print("• You can delete your data anytime")
        print("• No personal details are shared")
        
        while True:
            consent_input = input("\nWould you like me to remember helpful things from our conversations? (yes/no): ").strip().lower()
            
            if consent_input in ['yes', 'y']:
                if self.set_consent(True):
                    print("\n✅ Great! I'll remember important parts of our conversations to better support you.")
                    return True
                else:
                    print("❌ There was an error saving your preference. Please try again.")
                    return False
            elif consent_input in ['no', 'n']:
                if self.set_consent(False):
                    print("\n✅ Understood. I won't remember conversations between sessions.")
                    print("You can change this setting anytime by typing 'settings' during our chat.")
                    return True
                else:
                    print("❌ There was an error saving your preference. Please try again.")
                    return False
            else:
                print("Please answer 'yes' or 'no'.")

    def chat_loop(self):
        self.session_id = f"session_{int(time.time())}"
        display_name = self.user_profile.get("profile", {}).get("username", "Guest")

        print("\n" + "="*50)
        print("💬 EmpathicBot Chat Started!")
        print(f"👤 Signed in as: {display_name}")
        print("Type 'quit' or 'exit' to return to the main menu.")
        print("-" * 50)
        
        # Check if consent is needed
        consent_status = self.user_profile.get("profile", {}).get("consent")
        if consent_status is None:
            if not self.handle_consent_flow():
                print("❌ Unable to set privacy preferences. Returning to main menu.")
                return
            print("\nNow, what would you like to talk about?")
        
        while True:
            user_input = input(f"\nYou: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ['quit', 'exit']:
                break
            
            # Handle special commands
            if user_input.lower() == 'settings':
                print("\nCurrent Settings:")
                consent_status = self.user_profile.get("profile", {}).get("consent", False)
                print(f"Memory enabled: {'Yes' if consent_status else 'No'}")
                change = input("Would you like to change your memory setting? (yes/no): ").strip().lower()
                if change in ['yes', 'y']:
                    self.handle_consent_flow()
                continue

            print("\n🤖 EmpathicBot is thinking...")
            bot_response = self.send_message(user_input)
            
            print(f"\n🤖 EmpathicBot: {bot_response}")

    def run(self):
        print("\n" + "="*60)
        print("🤖 Welcome to the EmpathicBot Chat Client")
        print("="*60)

        while True:
            if not self.user_profile:
                print("\nYou are not signed in.")
                print("1. 🔑 Sign in with Google")
                print("2. 👤 Continue as Guest")
                print("3. ❌ Exit")
                choice = input("\nSelect an option: ").strip()

                if choice == '1':
                    self.sign_in_google()
                elif choice == '2':
                    self.sign_in_guest()
                elif choice == '3':
                    break
            else:
                print("\nMain Menu")
                print("1. 💬 Start Chatting")
                print("2. 🚪 Sign Out")
                choice = input("\nSelect an option: ").strip()

                if choice == '1':
                    self.chat_loop()
                elif choice == '2':
                    self.sign_out()

        print("\n👋 Goodbye! Take care!")

if __name__ == "__main__":
    client = AuthChatClient()
    client.run()