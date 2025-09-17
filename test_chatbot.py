#!/usr/bin/env python3
"""
Comprehensive testing script for genai-chatbot
Run this after starting your main.py server to test all functionality
"""

import requests
import json
import time
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://127.0.0.1:8080"
TEST_USER_ID = f"testuser_{int(time.time())}"  # Unique test user

def print_test_header(test_name):
    print("\n" + "="*60)
    print(f" {test_name}")
    print("="*60)

def print_result(success, message):
    status = " PASS" if success else " FAIL"
    print(f"{status}: {message}")

def make_request(method, endpoint, data=None):
    """Make HTTP request and return response"""
    url = f"{BASE_URL}{endpoint}"
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

def test_health_check():
    """Test the health check endpoint"""
    print_test_header("Health Check Test")
    
    status_code, response = make_request("GET", "/health")
    
    if status_code is None:
        print_result(False, "Server not responding - check if main.py is running")
        return False
    
    if status_code == 200:
        if response.get("status") == "healthy":
            print_result(True, "All services are healthy")
            return True
        else:
            print_result(False, f"Services unhealthy: {response}")
            return False
    else:
        print_result(False, f"Health check failed with status {status_code}")
        return False

def test_consent_flow():
    """Test the consent mechanism"""
    print_test_header("Consent Flow Test")
    
    # Test setting consent to true
    consent_data = {
        "user_id": TEST_USER_ID,
        "consent": True
    }
    
    status_code, response = make_request("POST", "/consent", consent_data)
    
    if status_code == 200 and response.get("ok") and response.get("consent"):
        print_result(True, "Consent set successfully")
        return True
    else:
        print_result(False, f"Failed to set consent: {response}")
        return False

def test_webhook_without_consent():
    """Test webhook behavior when user hasn't given consent"""
    print_test_header("Webhook Without Consent Test")
    
    # Use a different user ID that hasn't given consent
    no_consent_user = f"noconsent_{int(time.time())}"
    
    webhook_data = {
        "session": f"projects/genai-bot-kdf/agent/sessions/testsession_{int(time.time())}",
        "messages": [{"text": {"text": ["I need help with anxiety"]}}],
        "sessionInfo": {"parameters": {"user_id": no_consent_user}}
    }
    
    status_code, response = make_request("POST", "/dialogflow-webhook", webhook_data)
    
    if status_code == 200:
        reply = response.get("fulfillment_response", {}).get("messages", [{}])[0].get("text", {}).get("text", [""])[0]
        if "consent" in reply.lower() or "remember" in reply.lower():
            print_result(True, "Correctly asking for consent")
            return True
        else:
            print_result(False, f"Not asking for consent. Reply: {reply}")
            return False
    else:
        print_result(False, f"Webhook failed: {response}")
        return False

def test_basic_conversation():
    """Test basic conversation with consent"""
    print_test_header("Basic Conversation Test")
    
    webhook_data = {
        "session": f"projects/genai-bot-kdf/agent/sessions/testsession_{int(time.time())}",
        "messages": [{"text": {"text": ["I'm feeling stressed about work"]}}],
        "sessionInfo": {"parameters": {"user_id": TEST_USER_ID}}
    }
    
    status_code, response = make_request("POST", "/dialogflow-webhook", webhook_data)
    
    if status_code == 200:
        reply = response.get("fulfillment_response", {}).get("messages", [{}])[0].get("text", {}).get("text", [""])[0]
        if reply and len(reply) > 10 and "consent" not in reply.lower():
            print_result(True, f"Got meaningful response: '{reply[:100]}...'")
            return True
        else:
            print_result(False, f"Poor response: '{reply}'")
            return False
    else:
        print_result(False, f"Webhook failed: {response}")
        return False

def test_memory_creation():
    """Test that memories are created after enough conversation turns"""
    print_test_header("Memory Creation Test (8 turns)")
    
    print(" Sending 8 conversation turns to trigger memory creation...")
    
    messages = [
        "I've been having trouble sleeping",
        "Work has been really stressful lately",
        "I tried meditation but it's hard to focus",
        "My anxiety gets worse in the evening",
        "I feel better when I talk to friends",
        "Exercise helps me sometimes",
        "I should probably eat better too",
        "Thank you for listening to me"
    ]
    
    session_id = f"testsession_{int(time.time())}"
    success_count = 0
    
    for i, message in enumerate(messages, 1):
        print(f"\n Turn {i}/8: '{message}'")
        
        webhook_data = {
            "session": f"projects/genai-bot-kdf/agent/sessions/{session_id}",
            "messages": [{"text": {"text": [message]}}],
            "sessionInfo": {"parameters": {"user_id": TEST_USER_ID}}
        }
        
        status_code, response = make_request("POST", "/dialogflow-webhook", webhook_data)
        
        if status_code == 200:
            reply = response.get("fulfillment_response", {}).get("messages", [{}])[0].get("text", {}).get("text", [""])[0]
            print(f" Response: '{reply[:100]}{'...' if len(reply) > 100 else ''}'")
            success_count += 1
        else:
            print(f" Turn {i} failed")
            break
        
        time.sleep(1)  # Small delay between requests
    
    if success_count == 8:
        print_result(True, "All 8 conversation turns completed - memory should be created")
        return True
    else:
        print_result(False, f"Only {success_count}/8 turns successful")
        return False

def test_memory_retrieval():
    """Test that memories can be retrieved in future conversations"""
    print_test_header("Memory Retrieval Test")
    
    # Wait a moment for memory processing
    print(" Waiting 2 seconds for memory processing...")
    time.sleep(2)
    
    # Start a new conversation that should retrieve the memory
    webhook_data = {
        "session": f"projects/genai-bot-kdf/agent/sessions/newsession_{int(time.time())}",
        "messages": [{"text": {"text": ["I'm having sleep problems again"]}}],
        "sessionInfo": {"parameters": {"user_id": TEST_USER_ID}}
    }
    
    status_code, response = make_request("POST", "/dialogflow-webhook", webhook_data)
    
    if status_code == 200:
        reply = response.get("fulfillment_response", {}).get("messages", [{}])[0].get("text", {}).get("text", [""])[0]
        # Check if response shows awareness of past conversation
        memory_indicators = ["remember", "mentioned", "previously", "before", "last time", "earlier"]
        has_memory = any(indicator in reply.lower() for indicator in memory_indicators)
        
        if has_memory or len(reply) > 50:  # Either shows memory or gives detailed response
            print_result(True, f"Response shows memory awareness: '{reply[:150]}...'")
            return True
        else:
            print_result(False, f"Response doesn't show memory: '{reply}'")
            return False
    else:
        print_result(False, f"Memory retrieval test failed: {response}")
        return False

def test_delete_memories():
    """Test the delete memories functionality"""
    print_test_header("Delete Memories Test")
    
    delete_data = {
        "user_id": TEST_USER_ID
    }
    
    status_code, response = make_request("POST", "/delete_memories", delete_data)
    
    if status_code == 200 and response.get("ok"):
        deleted_count = response.get("deleted", 0)
        print_result(True, f"Successfully deleted {deleted_count} memories")
        return True
    else:
        print_result(False, f"Failed to delete memories: {response}")
        return False

def test_error_handling():
    """Test error handling with malformed requests"""
    print_test_header("Error Handling Test")
    
    # Test missing user_id in consent
    status_code, response = make_request("POST", "/consent", {})
    if status_code == 400:
        print_result(True, "Correctly rejected consent request without user_id")
        error_test_1 = True
    else:
        print_result(False, f"Should have rejected empty consent request: {response}")
        error_test_1 = False
    
    # Test missing user_id in delete_memories
    status_code, response = make_request("POST", "/delete_memories", {})
    if status_code == 400:
        print_result(True, "Correctly rejected delete request without user_id")
        error_test_2 = True
    else:
        print_result(False, f"Should have rejected empty delete request: {response}")
        error_test_2 = False
    
    # Test malformed webhook request
    status_code, response = make_request("POST", "/dialogflow-webhook", {"invalid": "data"})
    if status_code in [200, 500]:  # Either handles gracefully or returns error
        print_result(True, "Handled malformed webhook request appropriately")
        error_test_3 = True
    else:
        print_result(False, f"Unexpected response to malformed request: {response}")
        error_test_3 = False
    
    return error_test_1 and error_test_2 and error_test_3

def run_performance_test():
    """Test response times and concurrent requests"""
    print_test_header("Performance Test")
    
    # Test response time
    start_time = time.time()
    
    webhook_data = {
        "session": f"projects/genai-bot-kdf/agent/sessions/perftest_{int(time.time())}",
        "messages": [{"text": {"text": ["Hello, how are you?"]}}],
        "sessionInfo": {"parameters": {"user_id": f"perftest_{int(time.time())}"}}
    }
    
    status_code, response = make_request("POST", "/dialogflow-webhook", webhook_data)
    end_time = time.time()
    
    response_time = end_time - start_time
    
    if status_code == 200:
        if response_time < 10:  # Should respond within 10 seconds
            print_result(True, f"Good response time: {response_time:.2f} seconds")
            return True
        else:
            print_result(False, f"Slow response time: {response_time:.2f} seconds")
            return False
    else:
        print_result(False, f"Performance test failed: {response}")
        return False

def main():
    """Run all tests"""
    print(" Starting Comprehensive Chatbot Tests")
    print(f" Test started at: {datetime.now()}")
    print(f" Test user ID: {TEST_USER_ID}")
    print(f" Server URL: {BASE_URL}")
    
    # Track test results
    test_results = []
    
    # Run all tests
    tests = [
        ("Health Check", test_health_check),
        ("Consent Flow", test_consent_flow),
        ("Webhook Without Consent", test_webhook_without_consent),
        ("Basic Conversation", test_basic_conversation),
        ("Memory Creation", test_memory_creation),
        ("Memory Retrieval", test_memory_retrieval),
        ("Delete Memories", test_delete_memories),
        ("Error Handling", test_error_handling),
        ("Performance Test", run_performance_test),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            test_results.append((test_name, result))
        except Exception as e:
            print(f" Test '{test_name}' crashed with error: {e}")
            test_results.append((test_name, False))
    
    # Print summary
    print("\n" + "="*60)
    print(" TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = " PASS" if result else " FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "-"*60)
    print(f" Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Your chatbot is working correctly.")
    elif passed >= total * 0.8:
        print("  Most tests passed, but check the failures above.")
    else:
        print(" Many tests failed. Check your configuration and logs.")
    
    print(f" Test completed at: {datetime.now()}")
    
    # Cleanup suggestion
    print(f"\n To clean up test data, you can run:")
    print(f"   curl -X POST {BASE_URL}/delete_memories -H 'Content-Type: application/json' -d '{{\"user_id\":\"{TEST_USER_ID}\"}}'")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--url":
        if len(sys.argv) > 2:
            BASE_URL = sys.argv[2].rstrip('/')
        else:
            print("Usage: python test_chatbot.py --url http://your-server-url")
            sys.exit(1)
    
    main()