#!/usr/bin/env python3
"""
Interactive Chat Client for EmpathicBot
Connects to the Flask chatbot server and provides a user-friendly chat interface
"""

import requests
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import uuid
import re

# Configuration
CHATBOT_URL = "http://127.0.0.1:8080"
USERS_DATA_FILE = "chat_users_data.json"
CHAT_HISTORY_FILE = "chat_history.json"
CURRENT_USER_FILE = "current_user.json"

class EmpathicChatClient:
    def __init__(self):
        self.current_user_id = None
        self.session_id = None
        self.users_data = self.load_users_data()
        self.chat_history = self.load_chat_history()
        self.current_user_data = {}
        
    def sanitize_user_id(self, user_id):
        """Sanitize user_id to match server-side sanitization"""
        # Replace invalid characters with underscores
        sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)
        # Ensure it doesn't start with a number
        if sanitized and sanitized[0].isdigit():
            sanitized = f"user_{sanitized}"
        # Ensure minimum length
        if not sanitized:
            sanitized = "anonymous_user"
        return sanitized
        
    def load_users_data(self):
        """Load all users data"""
        if os.path.exists(USERS_DATA_FILE):
            try:
                with open(USERS_DATA_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return {}
    
    def save_users_data(self):
        """Save all users data"""
        try:
            with open(USERS_DATA_FILE, 'w') as f:
                json.dump(self.users_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save users data: {e}")
    
    def load_current_user(self):
        """Load the last active user"""
        if os.path.exists(CURRENT_USER_FILE):
            try:
                with open(CURRENT_USER_FILE, 'r') as f:
                    data = json.load(f)
                    return data.get("current_user_id")
            except:
                pass
        return None
    
    def save_current_user(self, user_id):
        """Save the current active user"""
        try:
            with open(CURRENT_USER_FILE, 'w') as f:
                json.dump({"current_user_id": user_id}, f)
        except Exception as e:
            print(f"⚠️  Warning: Could not save current user: {e}")
    
    def load_chat_history(self):
        """Load chat history for all users"""
        if os.path.exists(CHAT_HISTORY_FILE):
            try:
                with open(CHAT_HISTORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                pass
        return []
    
    def save_chat_history(self):
        """Save chat history"""
        try:
            # Keep only last 1000 messages total to prevent file from getting too large
            recent_history = self.chat_history[-1000:] if len(self.chat_history) > 1000 else self.chat_history
            with open(CHAT_HISTORY_FILE, 'w') as f:
                json.dump(recent_history, f, indent=2)
        except Exception as e:
            print(f"⚠️  Warning: Could not save chat history: {e}")
    
    def add_to_history(self, user_message, bot_response):
        """Add exchange to chat history"""
        self.chat_history.append({
            "timestamp": datetime.now().isoformat(),
            "user_id": self.current_user_id,
            "session_id": self.session_id,
            "user_message": user_message,
            "bot_response": bot_response
        })
        self.save_chat_history()
    
    def list_users(self):
        """List all registered users"""
        if not self.users_data:
            return []
        
        users_list = []
        for user_id, data in self.users_data.items():
            # Count messages for this user
            message_count = len([h for h in self.chat_history if h.get("user_id") == user_id])
            users_list.append({
                "user_id": user_id,
                "username": data.get("username", "Unknown"),
                "consent": data.get("consent", False),
                "created_date": data.get("created_date", ""),
                "last_chat_date": data.get("last_chat_date", ""),
                "message_count": message_count
            })
        
        # Sort by last chat date (most recent first)
        users_list.sort(key=lambda x: x["last_chat_date"], reverse=True)
        return users_list
    
    def select_user(self):
        """User selection menu"""
        print("\n" + "="*60)
        print("👥 User Selection")
        print("="*60)
        
        users = self.list_users()
        
        if users:
            print("Registered Users:")
            print("-" * 60)
            for i, user in enumerate(users, 1):
                username = user["username"]
                user_id = user["user_id"]
                consent = "✅" if user["consent"] else "❌"
                message_count = user["message_count"]
                
                # Format last chat date
                last_chat = user["last_chat_date"]
                if last_chat:
                    try:
                        dt = datetime.fromisoformat(last_chat.replace('Z', '+00:00'))
                        last_chat_str = dt.strftime("%Y-%m-%d %H:%M")
                    except:
                        last_chat_str = last_chat[:16]
                else:
                    last_chat_str = "Never"
                
                print(f"{i:2d}. {username} (ID: {user_id})")
                print(f"    Last chat: {last_chat_str} | Messages: {message_count} | Consent: {consent}")
                print()
            
            print(f"{len(users) + 1:2d}. ➕ Add New User")
            print(f"{len(users) + 2:2d}. 🗑️  Delete User")
            print(f"{len(users) + 3:2d}. ❌ Exit")
        else:
            print("No users found. Let's create your first user!")
            print("\n1. ➕ Add New User")
            print("2. ❌ Exit")
        
        print("-" * 60)
        
        try:
            if users:
                max_choice = len(users) + 3
                choice = input(f"Select option (1-{max_choice}): ").strip()
                
                if choice.isdigit():
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(users):
                        # Select existing user
                        selected_user = users[choice_num - 1]
                        self.current_user_id = selected_user["user_id"]
                        self.current_user_data = self.users_data[self.current_user_id]
                        self.save_current_user(self.current_user_id)
                        return "selected"
                    elif choice_num == len(users) + 1:
                        return "add_new"
                    elif choice_num == len(users) + 2:
                        return "delete_user"
                    elif choice_num == len(users) + 3:
                        return "exit"
            else:
                choice = input("Select option (1-2): ").strip()
                if choice == "1":
                    return "add_new"
                elif choice == "2":
                    return "exit"
            
            print("Invalid choice. Please try again.")
            return self.select_user()
            
        except (ValueError, KeyboardInterrupt):
            return "exit"
    
    def add_new_user(self):
        """Add a new user"""
        print("\n" + "="*50)
        print("➕ Add New User")
        print("="*50)
        
        # Get username
        username = input("Enter username: ").strip()
        if not username:
            username = "User"
        
        # Get user ID
        print(f"\nPlease choose a unique user ID.")
        print("This ID will be used to remember conversations across sessions.")
        print("Note: Special characters will be sanitized for database compatibility.")
        
        while True:
            custom_id = input("Enter user ID: ").strip()
            
            if not custom_id:
                print("User ID cannot be empty. Please try again.")
                continue
                
            # Show sanitized version
            sanitized_id = self.sanitize_user_id(custom_id)
            if sanitized_id != custom_id:
                print(f"ID will be sanitized to: {sanitized_id}")
                confirm = input("Continue with sanitized ID? (y/n): ").strip().lower()
                if confirm != 'y':
                    continue
                custom_id = sanitized_id
                
            if custom_id in self.users_data:
                print(f"User ID '{custom_id}' already exists. Please choose a different one.")
                continue
            
            break
        
        print(f"\nUser ID: {custom_id}")
        print("Save this ID - you'll need it to resume conversations later!")
        
        print("\nEmpathicBot will ask for your consent when you start chatting.")
        print("The bot can remember helpful things from conversations to provide")
        print("better support across sessions.")
        
        # Save user data
        user_data = {
            "user_id": custom_id,
            "username": username,
            "consent": None,  # Will be set during first chat
            "created_date": datetime.now().isoformat(),
            "last_chat_date": datetime.now().isoformat()
        }
        
        self.users_data[custom_id] = user_data
        self.save_users_data()
        
        # Set as current user
        self.current_user_id = custom_id
        self.current_user_data = user_data
        self.save_current_user(custom_id)
        
        # Send the initial profile data (username) to the server
        try:
            requests.post(
                f"{CHATBOT_URL}/consent",
                json={"user_id": custom_id, "username": username},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            print("✅ User profile synced with server.")
        except Exception as e:
            print(f"⚠️  Warning: Could not sync new user profile with server: {e}")
        
        print(f"✅ User '{username}' created successfully!")
        return True
    
    def delete_user(self):
        """Delete a user"""
        users = self.list_users()
        if not users:
            print("No users to delete.")
            return
        
        print("\n" + "="*50)
        print("🗑️  Delete User")
        print("="*50)
        
        print("Select user to delete:")
        for i, user in enumerate(users, 1):
            print(f"{i}. {user['username']} (ID: {user['user_id']}) - {user['message_count']} messages")
        
        print(f"{len(users) + 1}. Cancel")
        
        try:
            choice = input(f"\nSelect user to delete (1-{len(users) + 1}): ").strip()
            
            if choice.isdigit():
                choice_num = int(choice)
                if 1 <= choice_num <= len(users):
                    selected_user = users[choice_num - 1]
                    user_id = selected_user["user_id"]
                    username = selected_user["username"]
                    
                    print(f"\n⚠️  You are about to delete user: {username} (ID: {user_id})")
                    print("This will:")
                    print("- Remove user from local database")
                    print("- Delete server-side memories for this user")
                    print("- Remove chat history for this user")
                    
                    confirm = input("\nType 'DELETE' to confirm: ").strip()
                    
                    if confirm == "DELETE":
                        # Delete from server
                        try:
                            response = requests.post(
                                f"{CHATBOT_URL}/delete_memories",
                                json={"user_id": user_id},
                                headers={"Content-Type": "application/json"},
                                timeout=10
                            )
                            
                            if response.status_code == 200:
                                data = response.json()
                                deleted_count = data.get("deleted", 0)
                                print(f"✅ Deleted {deleted_count} server memories for {username}")
                            else:
                                print(f"⚠️  Warning: Could not delete server memories (status: {response.status_code})")
                        except Exception as e:
                            print(f"⚠️  Warning: Error deleting server memories: {e}")
                        
                        # Remove from local data
                        del self.users_data[user_id]
                        self.save_users_data()
                        
                        # Remove chat history
                        self.chat_history = [h for h in self.chat_history if h.get("user_id") != user_id]
                        self.save_chat_history()
                        
                        # Clear current user if deleted
                        if self.current_user_id == user_id:
                            self.current_user_id = None
                            self.current_user_data = {}
                            if os.path.exists(CURRENT_USER_FILE):
                                os.remove(CURRENT_USER_FILE)
                        
                        print(f"✅ User '{username}' deleted successfully!")
                    else:
                        print("❌ Deletion cancelled.")
                elif choice_num == len(users) + 1:
                    print("❌ Deletion cancelled.")
        except (ValueError, KeyboardInterrupt):
            print("❌ Deletion cancelled.")
    
    def send_message(self, message):
        """Send message to EmpathicBot and return response"""
        webhook_data = {
            "session": f"projects/genai-bot-kdf/agent/sessions/{self.session_id}",
            "messages": [{"text": {"text": [message]}}],
            "sessionInfo": {"parameters": {"user_id": self.current_user_id}}
        }
        
        try:
            response = requests.post(
                f"{CHATBOT_URL}/dialogflow-webhook",
                json=webhook_data,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                bot_response = data.get("fulfillment_response", {}).get("messages", [{}])[0].get("text", {}).get("text", [""])[0]
                return bot_response
            else:
                return f"Error: Server returned {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            return "❌ Connection Error: Is the EmpathicBot server running on port 8080?"
        except requests.exceptions.Timeout:
            return "❌ Timeout: The server is taking too long to respond."
        except Exception as e:
            return f"❌ Error: {e}"
    
    def handle_consent_response(self, user_input):
        """Handle user's consent response"""
        if user_input.lower() in ['yes', 'y', 'ok', 'sure', 'yeah', 'yep']:
            consent_bool = True
        elif user_input.lower() in ['no', 'n', 'nope', 'nah']:
            consent_bool = False
        else:
            print("Please answer 'yes' or 'no'")
            return None
        
        try:
            response = requests.post(
                f"{CHATBOT_URL}/consent",
                json={"user_id": self.current_user_id, "consent": consent_bool},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                self.current_user_data["consent"] = consent_bool
                self.users_data[self.current_user_id] = self.current_user_data
                self.save_users_data()
                
                if consent_bool:
                    print("✅ Great! EmpathicBot will remember helpful things from our conversations.")
                else:
                    print("✅ Understood. EmpathicBot won't remember conversations between sessions.")
                
                return consent_bool
            else:
                print("❌ Error setting consent. Please try again.")
                return None
                
        except Exception as e:
            print(f"❌ Error: {e}")
            return None
    
    def chat_loop(self):
        """Main chat interaction loop"""
        username = self.current_user_data.get('username', 'User')
        user_id = self.current_user_id
        
        print(f"\n💬 EmpathicBot Chat Started!")
        print(f"👤 User: {username} (ID: {user_id})")
        print(f"🔗 Session: {self.session_id}")
        
        consent_status = self.current_user_data.get('consent')
        if consent_status is not None:
            print(f"🛡️  Memory Consent: {'Yes' if consent_status else 'No'}")
        else:
            print(f"🛡️  Memory Consent: Will be asked during chat")
        
        print("\nType '/menu' to access options, or 'quit' to exit chat.")
        print("EmpathicBot is here to listen and support you.")
        print("-" * 50)
        
        # Check if this is first time and consent is needed
        awaiting_consent = self.current_user_data.get('consent') is None
        
        while True:
            try:
                # Get user input
                user_input = input(f"\n{username}: ").strip()
                
                # Check for commands
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    print(f"\n👋 Take care, {username}! Remember, you're not alone.")
                    break
                
                if user_input.lower() == '/menu':
                    self.show_chat_menu()
                    continue
                
                if user_input.lower() == '/switch':
                    print(f"\n👥 Switching users...")
                    return "switch_user"
                
                if user_input.lower() == '/history':
                    self.show_user_history(user_id, limit=5)
                    continue
                
                if user_input.lower() == '/newsession':
                    self.session_id = f"session_{int(time.time())}_{user_id}"
                    print(f"🔄 Started new session: {self.session_id}")
                    continue
                
                if not user_input:
                    continue
                
                # If awaiting consent and user gives consent response
                if awaiting_consent:
                    consent_result = self.handle_consent_response(user_input)
                    if consent_result is not None:
                        awaiting_consent = False
                        continue
                    # If not a valid consent response, continue with normal chat
                
                # Show typing indicator
                print("🤖 EmpathicBot is thinking...")
                
                # Send message and get response
                bot_response = self.send_message(user_input)
                
                # Check if bot is asking for consent
                if "remember" in bot_response.lower() and "consent" in bot_response.lower():
                    awaiting_consent = True
                
                # Display response
                print(f"\n🤖 EmpathicBot: {bot_response}")
                
                # Add to history
                self.add_to_history(user_input, bot_response)
                
                # Update last chat date
                self.current_user_data["last_chat_date"] = datetime.now().isoformat()
                self.users_data[self.current_user_id] = self.current_user_data
                self.save_users_data()
                
            except KeyboardInterrupt:
                print(f"\n\n👋 Chat interrupted. Take care, {username}!")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                print("Type 'quit' to exit safely.")
        
        return "main_menu"
    
    def show_chat_menu(self):
        """Show in-chat menu"""
        print("\n" + "="*40)
        print("💬 Chat Menu")
        print("="*40)
        print("Commands:")
        print("  /menu       - Show this menu")
        print("  /switch     - Switch to different user")
        print("  /history    - Show recent chat history")
        print("  /newsession - Start a new session")
        print("  quit        - Exit chat")
        print("-" * 40)
    
    def show_user_history(self, user_id, limit=10):
        """Show recent chat history for specific user"""
        user_history = [h for h in self.chat_history if h.get("user_id") == user_id]
        
        if not user_history:
            print(f"\n📝 No chat history found.")
            return
        
        # Show recent messages
        recent = user_history[-limit:] if len(user_history) > limit else user_history
        
        print(f"\n📖 Recent Chat History (last {len(recent)} messages)")
        print("-" * 50)
        
        for entry in recent:
            timestamp = entry.get("timestamp", "")
            session_id = entry.get("session_id", "unknown")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%m-%d %H:%M")
                except:
                    time_str = timestamp[:16]
            else:
                time_str = "Unknown"
            
            user_msg = entry.get('user_message', '')
            bot_msg = entry.get('bot_response', '')
            
            print(f"[{time_str}] (Session: {session_id[:8]}...)")
            print(f"You: {user_msg[:100]}{'...' if len(user_msg) > 100 else ''}")
            print(f"EmpathicBot: {bot_msg[:100]}{'...' if len(bot_msg) > 100 else ''}")
            print()
    
    def main_menu(self):
        """Show main application menu"""
        while True:
            current_user = self.current_user_data.get('username', 'None') if self.current_user_id else 'None'
            
            print("\n" + "="*60)
            print("🤖 EmpathicBot Chat Client")
            print("="*60)
            print(f"👤 Current User: {current_user}")
            
            if self.current_user_id:
                message_count = len([h for h in self.chat_history if h.get("user_id") == self.current_user_id])
                consent_status = self.current_user_data.get('consent')
                if consent_status is not None:
                    consent_icon = "✅" if consent_status else "❌"
                else:
                    consent_icon = "❓"
                print(f"💬 Messages: {message_count} | 🛡️  Consent: {consent_icon}")
            
            print("\nOptions:")
            print("1. 💬 Start Chat")
            print("2. 👥 Switch/Select User")
            print("3. ➕ Add New User")
            print("4. 📖 View All Users")
            print("5. 🗑️  Delete User")
            print("6. ⚙️  Settings")
            print("7. ❌ Exit")
            print("-" * 60)
            
            choice = input("Select option (1-7): ").strip()
            
            if choice == "1":
                if not self.current_user_id:
                    print("\n⚠️  Please select a user first!")
                    continue
                
                # Generate unique session ID with user context
                self.session_id = f"session_{int(time.time())}_{self.current_user_id}"
                result = self.chat_loop()
                if result == "switch_user":
                    user_action = self.select_user()
                    if user_action == "exit":
                        break
            
            elif choice == "2":
                user_action = self.select_user()
                if user_action == "exit":
                    break
                elif user_action == "add_new":
                    self.add_new_user()
                elif user_action == "delete_user":
                    self.delete_user()
            
            elif choice == "3":
                self.add_new_user()
            
            elif choice == "4":
                self.show_all_users()
            
            elif choice == "5":
                self.delete_user()
            
            elif choice == "6":
                self.settings_menu()
            
            elif choice == "7":
                print("\n👋 Goodbye! Take care!")
                break
            
            else:
                print("Invalid choice. Please try again.")
    
    def show_all_users(self):
        """Display detailed information about all users"""
        users = self.list_users()
        
        if not users:
            print("\nNo users found.")
            return
        
        print(f"\n👥 All Users ({len(users)} total)")
        print("="*70)
        
        for i, user in enumerate(users, 1):
            username = user["username"]
            user_id = user["user_id"] 
            consent = user["consent"]
            if consent is None:
                consent_str = "Not set"
            else:
                consent_str = "Yes" if consent else "No"
            message_count = user["message_count"]
            
            created_date = user["created_date"]
            if created_date:
                try:
                    dt = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                    created_str = dt.strftime("%Y-%m-%d")
                except:
                    created_str = created_date[:10]
            else:
                created_str = "Unknown"
            
            last_chat = user["last_chat_date"]
            if last_chat:
                try:
                    dt = datetime.fromisoformat(last_chat.replace('Z', '+00:00'))
                    last_chat_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    last_chat_str = last_chat[:16]
            else:
                last_chat_str = "Never"
            
            active = "🟢" if user_id == self.current_user_id else "⚪"
            
            print(f"{i:2d}. {active} {username}")
            print(f"    ID: {user_id}")
            print(f"    Created: {created_str} | Last Chat: {last_chat_str}")
            print(f"    Messages: {message_count} | Consent: {consent_str}")
            print()
        
        input("Press Enter to continue...")
    
    def settings_menu(self):
        """Settings and configuration menu"""
        if not self.current_user_id:
            print("\n⚠️  Please select a user first!")
            return
        
        while True:
            user_data = self.current_user_data
            username = user_data.get('username', 'Unknown')
            
            print(f"\n⚙️  Settings - {username}")
            print("="*40)
            print(f"👤 Username: {username}")
            print(f"🆔 User ID: {self.current_user_id}")
            
            consent = user_data.get('consent')
            if consent is None:
                consent_str = "Not set (will be asked during chat)"
            else:
                consent_str = "Yes" if consent else "No"
            print(f"🛡️  Memory Consent: {consent_str}")
            
            print(f"📅 Account Created: {user_data.get('created_date', 'Unknown')[:10]}")
            
            message_count = len([h for h in self.chat_history if h.get("user_id") == self.current_user_id])
            session_count = len(set([h.get("session_id") for h in self.chat_history if h.get("user_id") == self.current_user_id and h.get("session_id")]))
            print(f"💬 Total Messages: {message_count}")
            print(f"🔗 Total Sessions: {session_count}")
            
            print("\nOptions:")
            print("1. Change Username")
            print("2. Reset Memory Consent")
            print("3. View Full Chat History")
            print("4. Delete My Memories")
            print("5. Back to Main Menu")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == '1':
                new_username = input(f"Enter new username (current: {username}): ").strip()
                if new_username and new_username != username:
                    self.current_user_data["username"] = new_username
                    self.users_data[self.current_user_id] = self.current_user_data
                    self.save_users_data()
                    print(f"✅ Username changed to: {new_username}")
            
            elif choice == '2':
                print(f"\nThis will reset your consent preference.")
                print("EmpathicBot will ask for consent again during your next chat.")
                confirm = input("Reset consent? (y/n): ").strip().lower()
                if confirm == 'y':
                    self.current_user_data["consent"] = None
                    self.users_data[self.current_user_id] = self.current_user_data
                    self.save_users_data()
                    print("✅ Consent preference reset. You'll be asked again during chat.")
            
            elif choice == '3':
                self.view_full_history()
            
            elif choice == '4':
                self.delete_user_memories()
            
            elif choice == '5':
                break
            
            else:
                print("Invalid choice. Please try again.")
    
    def view_full_history(self):
        """View complete chat history for current user"""
        user_history = [h for h in self.chat_history if h.get("user_id") == self.current_user_id]
        
        if not user_history:
            print(f"\n📝 No chat history found.")
            return
        
        print(f"\n📖 Complete Chat History ({len(user_history)} messages)")
        print("="*60)
        
        for i, entry in enumerate(user_history, 1):
            timestamp = entry.get("timestamp", "")
            session_id = entry.get("session_id", "unknown")
            if timestamp:
                try:
                    dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except:
                    time_str = timestamp
            else:
                time_str = "Unknown time"
            
            print(f"\n[{i}] {time_str} (Session: {session_id})")
            print(f"You: {entry.get('user_message', '')}")
            print(f"EmpathicBot: {entry.get('bot_response', '')}")
            
            # Pause every 10 messages
            if i % 10 == 0 and i < len(user_history):
                cont = input(f"\nShowing {i}/{len(user_history)} messages. Continue? (y/n): ").strip().lower()
                if cont != 'y':
                    break
        
        input("\nPress Enter to continue...")
    
    def delete_user_memories(self):
        """Delete server-side memories for current user"""
        username = self.current_user_data.get('username', 'User')
        
        print(f"\n🗑️  Delete Memories - {username}")
        print("="*30)
        print("This will delete all memories stored on the server for your user ID.")
        print("Local chat history can optionally be deleted too.")
        
        confirm = input(f"\n❓ Delete server memories for {username}? (y/n): ").strip().lower()
        
        if confirm != 'y':
            print("❌ Deletion cancelled.")
            return
        
        try:
            response = requests.post(
                f"{CHATBOT_URL}/delete_memories",
                json={"user_id": self.current_user_id},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                deleted_count = data.get("deleted", 0)
                print(f"✅ Successfully deleted {deleted_count} server memories.")
            else:
                print(f"❌ Error: Server returned {response.status_code}")
        
        except Exception as e:
            print(f"❌ Error deleting memories: {e}")
        
        # Option to delete local history too
        delete_local = input(f"\n❓ Also delete local chat history for {username}? (y/n): ").strip().lower()
        if delete_local == 'y':
            try:
                # Remove only this user's history
                self.chat_history = [h for h in self.chat_history if h.get("user_id") != self.current_user_id]
                self.save_chat_history()
                print("✅ Local chat history deleted.")
            except Exception as e:
                print(f"❌ Error deleting local history: {e}")
    
    def run(self):
        """Main application loop"""
        try:
            # Check if server is running
            try:
                response = requests.get(f"{CHATBOT_URL}/health", timeout=5)
                server_status = "✅ Healthy" if response.status_code == 200 else "⚠️  Issues detected"
            except:
                print("❌ Cannot connect to EmpathicBot server!")
                print(f"Make sure the server is running on {CHATBOT_URL}")
                print("Run: python main.py")
                return
            
            print(f"🔗 Server: {CHATBOT_URL} - {server_status}")
            
            # Load last active user if exists
            last_user_id = self.load_current_user()
            if last_user_id and last_user_id in self.users_data:
                self.current_user_id = last_user_id
                self.current_user_data = self.users_data[last_user_id]
                print(f"👤 Resuming session for: {self.current_user_data.get('username', 'Unknown')}")
            
            # Start main menu
            self.main_menu()
        
        except KeyboardInterrupt:
            print("\n\nApplication interrupted. Goodbye!")
        except Exception as e:
            print(f"\nUnexpected error: {e}")

def main():
    """Entry point"""
    if len(sys.argv) > 1:
        if sys.argv[1] == "--url" and len(sys.argv) > 2:
            global CHATBOT_URL
            CHATBOT_URL = sys.argv[2].rstrip('/')
        elif sys.argv[1] in ["--help", "-h"]:
            print("Interactive Chat Client for EmpathicBot")
            print("\nUsage:")
            print("  python chat.py                    # Use default URL")
            print("  python chat.py --url http://...   # Use custom URL")
            print("\nFeatures:")
            print("  - Multiple user support with persistent data")
            print("  - Chat history and session management")
            print("  - Memory consent handling")
            print("  - User-friendly command interface")
            print("  - Connects to EmpathicBot Flask server")
            return

    client = EmpathicChatClient()
    client.run()

if __name__ == "__main__":
    main()