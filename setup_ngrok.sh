#!/bin/bash
# Setup script for ngrok tunnel to test Twilio webhooks locally

echo "========================================="
echo "       Ngrok Setup for Twilio Testing"
echo "========================================="
echo ""

# Check if ngrok is installed
if ! command -v ngrok &> /dev/null; then
    echo "❌ ngrok is not installed. Please run: brew install ngrok"
    exit 1
fi

# Check if authtoken is configured
if ! ngrok config check &> /dev/null; then
    echo "⚠️  Ngrok requires authentication (free account)"
    echo ""
    echo "Please follow these steps:"
    echo "1. Sign up for a free account at: https://dashboard.ngrok.com/signup"
    echo "2. Get your authtoken from: https://dashboard.ngrok.com/get-started/your-authtoken"
    echo "3. Run this command with your token:"
    echo "   ngrok config add-authtoken YOUR_AUTHTOKEN_HERE"
    echo ""
    echo "After setting up your authtoken, run this script again."
    exit 1
fi

# Check if backend is running
if ! curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "⚠️  Backend is not running. Please start it first:"
    echo "   cd api"
    echo "   source .venv/bin/activate"
    echo "   python -m uvicorn index:app --reload --host 0.0.0.0"
    echo ""
    exit 1
fi

echo "✅ Backend is running on http://localhost:8000"
echo ""
echo "Starting ngrok tunnel..."
echo "========================================="
echo ""

# Start ngrok and show the public URL
ngrok http 8000 --log=stdout | while IFS= read -r line; do
    if [[ $line == *"url="* ]]; then
        URL=$(echo "$line" | grep -oE 'https://[a-z0-9-]+\.ngrok[-a-z0-9]*\.app')
        if [ ! -z "$URL" ]; then
            echo ""
            echo "🎉 Ngrok tunnel is ready!"
            echo "========================================="
            echo ""
            echo "Public URL: $URL"
            echo ""
            echo "Twilio Webhook URL: $URL/twilio/webhooks/sms"
            echo ""
            echo "Next steps:"
            echo "1. Go to Twilio Console: https://console.twilio.com"
            echo "2. Navigate to Phone Numbers > Manage > Active Numbers"
            echo "3. Click on your phone number"
            echo "4. In the Messaging section, set:"
            echo "   - When a message comes in:"
            echo "     Webhook: $URL/twilio/webhooks/sms"
            echo "     HTTP Method: POST"
            echo "5. Save the configuration"
            echo ""
            echo "Test by sending an SMS to your Twilio number!"
            echo ""
            echo "Press Ctrl+C to stop the tunnel"
            echo "========================================="
        fi
    fi
done