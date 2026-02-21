#!/usr/bin/env python3
"""
Test script for SMS integration with the emergency agent.
This simulates what happens when Twilio receives an SMS.
"""

import requests
import json
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"
TEST_PHONE = "+1234567890"  # Replace with your test phone number

def test_sms_webhook():
    """Test the Twilio webhook endpoint with a simulated SMS"""

    # Simulate Twilio webhook payload
    twilio_payload = {
        "MessageSid": f"TEST{datetime.now().isoformat()}",
        "AccountSid": "ACtest123",
        "From": TEST_PHONE,
        "To": "+19876543210",  # Your Twilio number
        "Body": "Hello, I need help with an emergency",
        "NumMedia": "0"
    }

    print("Testing SMS webhook...")
    print(f"Sending message from {TEST_PHONE}: '{twilio_payload['Body']}'")

    try:
        # Send as form data (how Twilio sends it)
        response = requests.post(
            f"{API_URL}/twilio/webhooks/sms",
            data=twilio_payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )

        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print(f"Response Body: {response.text}")

        if response.status_code == 200:
            print("\n✅ Webhook processed successfully!")
            print("Check your database for the stored messages and any created cases.")
            print("In production, an SMS response would be sent back to the phone number.")
        else:
            print(f"\n❌ Webhook failed with status {response.status_code}")

    except Exception as e:
        print(f"\n❌ Error testing webhook: {e}")

def test_chat_endpoint():
    """Test the chat endpoint directly"""

    chat_request = {
        "message": "I'm at 123 Main Street and my car broke down",
        "conversation_history": [
            {"role": "user", "content": "Hello I need help"},
            {"role": "assistant", "content": "I'm here to help. What's your emergency and location?"}
        ],
        "user_id": TEST_PHONE
    }

    print("\n\nTesting chat endpoint...")
    print(f"Message: '{chat_request['message']}'")

    try:
        response = requests.post(
            f"{API_URL}/chat",
            json=chat_request,
            headers={"Content-Type": "application/json"}
        )

        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("\n✅ Chat response received!")
            print(f"Response: {data.get('response', 'No response')[:200]}...")
            if data.get('case_id'):
                print(f"Case Created: {data['case_id']}")
            if data.get('extracted_info'):
                print(f"Extracted Info: {json.dumps(data['extracted_info'], indent=2)}")
        else:
            print(f"\n❌ Chat failed with status {response.status_code}")
            print(f"Error: {response.text}")

    except Exception as e:
        print(f"\n❌ Error testing chat: {e}")

def check_api_health():
    """Check if the API is running"""
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ API is running")
            return True
        else:
            print(f"❌ API returned status {response.status_code}")
            return False
    except:
        print("❌ Cannot connect to API at", API_URL)
        print("Make sure the backend is running: cd api && source .venv/bin/activate && python -m uvicorn index:app --reload")
        return False

if __name__ == "__main__":
    print("SMS Integration Test Script")
    print("=" * 40)

    if not check_api_health():
        exit(1)

    print("\nWhat would you like to test?")
    print("1. Test SMS webhook (simulates incoming SMS)")
    print("2. Test chat endpoint directly")
    print("3. Test both")

    choice = input("\nEnter choice (1-3): ").strip()

    if choice == "1":
        test_sms_webhook()
    elif choice == "2":
        test_chat_endpoint()
    elif choice == "3":
        test_sms_webhook()
        test_chat_endpoint()
    else:
        print("Invalid choice")