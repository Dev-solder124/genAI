
import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8080"
TEST_USER_ID = f"testuser_instructions_{int(time.time())}"
# Generate a unique user ID for the test
user_id = f"test_user_{int(time.time())}"

# Define the authorization token
token = "test_token"

def print_test_header(test_name):
    print("\n" + "="*60)
    print(f" {test_name}")
    print("="*60)

def print_result(success, message):
    status = " PASS" if success else " FAIL"
    print(f"{status}: {message}")

def make_request(method, endpoint, data=None, headers=None):
    """Make HTTP request and return response"""
    url = f"{BASE_URL}{endpoint}"
    if headers is None:
        headers = {"Content-Type": "application/json"}
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        else:
            response = requests.post(url, headers=headers, json=data, timeout=30)
        
        print(f" {method} {endpoint}")
        print(f" Request: {json.dumps(data, indent=2) if data else 'No body'}")
        print(f"  Status: {response.status_code}")
        
        try:
            response_data = response.json()
            print(f"  Response: {json.dumps(response_data, indent=2)}")
        except:
            print(f"  Response: {response.text}")
            response_data = {"raw_text": response.text}
        
        return response.status_code, response_data
    
    except requests.exceptions.ConnectionError:
        print(" Connection Error: Is the server running on port 8080?")
        return None, None
    except requests.exceptions.Timeout:
        print(" Timeout Error: Server took too long to respond")
        return None, None
    except Exception as e:
        print(f" Request Error: {e}")
        return None, None

def test_instruction_flow():
    """Test the entire instruction creation and retrieval flow"""
    print_test_header("Global User Instruction Flow Test")

    # 1. Set consent for the user
    print("\n--- Step 1: Setting Consent ---")
    consent_data = {
        "user_id": user_id,
        "consent": True,
        "username": "InstructionTester"
    }
    
    status_code, response = make_request("POST", "/consent", data=consent_data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    
    if status_code != 200 or not response.get('profile', {}).get('consent'):
        print_result(False, "Failed to set consent.")
        return False
    print_result(True, "Consent set successfully.")

    # 2. Have a conversation where the user gives an instruction
    print("\n--- Step 2: Giving an Instruction ---")
    instruction_message = "From now on, I want you to call me 'Captain'."
    webhook_data = {
        "session": f"projects/genai-bot-kdf/agent/sessions/instruction_test_{int(time.time())}",
        "messages": [{"text": {"text": [instruction_message]}}],
        "sessionInfo": {"parameters": {"user_id": user_id}}
    }
    
    status_code, response = make_request("POST", "/dialogflow-webhook", data=webhook_data, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})
    
    if status_code != 200:
        print_result(False, "Webhook call failed during instruction.")
        return False
    
    reply = response.get("fulfillment_response", {}).get("messages", [{}])[0].get("text", {}).get("text", [""`])[0]
    print(f" Assistant's reply to instruction: {reply}")
    print_result(True, "Webhook call for instruction was successful.")
    
    # Give the server a moment to process and save the instruction
    print("\n--- Waiting 5 seconds for instruction to be saved... ---")
    time.sleep(5)

    # 3. Start a new conversation to see if the instruction is followed
    print("\n--- Step 3: Verifying the Instruction ---")
    follow_up_message = "What do you remember about me?"
    webhook_data_2 = {
        "session": f"projects/genai-bot-kdf/agent/sessions/instruction_verify_{int(time.time())}",
        "messages": [{"text": {"text": [follow_up_message]}}],
        "sessionInfo": {"parameters": {"user_id": user_id}}
    }

    status_code, response = make_request("POST", "/dialogflow-webhook", data=webhook_data_2, headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"})

    if status_code != 200:
        print_result(False, "Webhook call failed during verification.")
        return False

    final_reply = response.get("fulfillment_response", {}).get("messages", [{}])[0].get("text", {}).get("text", [""`])[0]
    print(f" Assistant's reply for verification: {final_reply}")

    if 'captain' in final_reply.lower():
        print_result(True, "Instruction was successfully followed in a new conversation.")
        return True
    else:
        print_result(False, "Instruction was NOT followed in the new conversation.")
        return False

def main():
    """Run all tests"""
    print(" Starting Global User Instruction Test")
    print(f" Test started at: {datetime.now()}")
    print(f" Test user ID: {user_id}")
    print(f" Server URL: {BASE_URL}")
    
    # Run the test
    result = test_instruction_flow()
    
    # Print summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    
    if result:
        print("🎉 GLOBAL USER INSTRUCTION TEST PASSED!")
    else:
        print("❌ GLOBAL USER INSTRUCTION TEST FAILED.")
    
    print(f" Test completed at: {datetime.now()}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--url":
        if len(sys.argv) > 2:
            BASE_URL = sys.argv[2].rstrip('/')
        else:
            print("Usage: python test_instructions.py --url http://your-server-url")
            sys.exit(1)
    
    main()
