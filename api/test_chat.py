#!/usr/bin/env python3
"""
Test the chat endpoint directly
"""
import requests
import json

# Test the chat endpoint
url = "http://localhost:8000/chat"

# First message
print("Testing chat endpoint...")
response = requests.post(url, json={
    "message": "Hi, my name is John Smith and I need help",
    "conversation_history": [],
    "user_id": "test-user-1"
})

if response.ok:
    data = response.json()
    print("\n✅ First message successful!")
    print(f"AI Response: {data['response']}")
    print(f"Case ID: {data.get('case_id', 'None yet')}")
    print(f"Extracted Info: {json.dumps(data.get('extracted_info', {}), indent=2)}")

    # Second message with SSN
    print("\n" + "="*50)
    print("Sending second message with SSN...")

    conversation_history = [
        {"role": "user", "content": "Hi, my name is John Smith and I need help"},
        {"role": "assistant", "content": data['response']}
    ]

    response2 = requests.post(url, json={
        "message": "My social security number is 123-45-6789",
        "conversation_history": conversation_history,
        "user_id": "test-user-1"
    })

    if response2.ok:
        data2 = response2.json()
        print(f"\nAI Response: {data2['response']}")
        print(f"Case ID: {data2.get('case_id', 'None yet')}")
        print(f"Extracted Info: {json.dumps(data2.get('extracted_info', {}), indent=2)}")

        # Third message with location
        print("\n" + "="*50)
        print("Sending third message with location...")

        conversation_history.extend([
            {"role": "user", "content": "My social security number is 123-45-6789"},
            {"role": "assistant", "content": data2['response']}
        ])

        response3 = requests.post(url, json={
            "message": "I'm on Highway 95 near mile marker 42",
            "conversation_history": conversation_history,
            "user_id": "test-user-1"
        })

        if response3.ok:
            data3 = response3.json()
            print(f"\nAI Response: {data3['response']}")
            print(f"Case ID: {data3.get('case_id', 'None yet')}")
            print(f"Extracted Info: {json.dumps(data3.get('extracted_info', {}), indent=2)}")

            # Fourth message with emergency
            print("\n" + "="*50)
            print("Sending fourth message with emergency description...")

            conversation_history.extend([
                {"role": "user", "content": "I'm on Highway 95 near mile marker 42"},
                {"role": "assistant", "content": data3['response']}
            ])

            response4 = requests.post(url, json={
                "message": "I'm out of fuel and stuck in a blizzard. It's getting very cold.",
                "conversation_history": conversation_history,
                "user_id": "test-user-1"
            })

            if response4.ok:
                data4 = response4.json()
                print(f"\nAI Response: {data4['response']}")
                print(f"Case ID: {data4.get('case_id', 'None yet')}")
                print(f"Extracted Info: {json.dumps(data4.get('extracted_info', {}), indent=2)}")
            else:
                print(f"❌ Fourth message failed: {response4.status_code}")
                print(response4.text)
        else:
            print(f"❌ Third message failed: {response3.status_code}")
            print(response3.text)
    else:
        print(f"❌ Second message failed: {response2.status_code}")
        print(response2.text)
else:
    print(f"❌ First message failed: {response.status_code}")
    print(response.text)