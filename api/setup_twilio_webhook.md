# Setting Up Twilio SMS Integration

## Prerequisites
1. A Twilio account with an active phone number
2. Your backend API running and accessible from the internet (use ngrok for local testing)

## Configuration Steps

### 1. Set Environment Variables
Ensure these are set in your `.env` file:
- `TWILIO_ACCOUNT_SID`: Your Twilio Account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio Auth Token
- `TWILIO_FROM_NUMBER`: Your Twilio phone number (format: +1234567890)

### 2. Configure Twilio Webhook

#### For Local Development (using ngrok):
1. Install ngrok: `brew install ngrok` (on macOS)
2. Start your backend: `cd api && source .venv/bin/activate && python -m uvicorn index:app --reload --host 0.0.0.0`
3. In another terminal, expose your local server: `ngrok http 8000`
4. Copy the ngrok URL (e.g., `https://abc123.ngrok.io`)

#### Configure in Twilio Console:
1. Go to [Twilio Console](https://console.twilio.com)
2. Navigate to Phone Numbers > Manage > Active Numbers
3. Click on your phone number
4. In the Messaging section, set:
   - **When a message comes in**:
     - Webhook: `https://your-domain.com/twilio/webhooks/sms` (or your ngrok URL for local testing)
     - HTTP Method: `POST`
5. Save the configuration

### 3. Test the Integration

Send an SMS to your Twilio phone number. The message will:
1. Be received by the Twilio webhook
2. Get processed by the AI emergency agent
3. Generate a response that gets sent back via SMS
4. Maintain conversation context across messages

## How It Works

1. **Incoming SMS**: When someone texts your Twilio number, Twilio sends a POST request to `/twilio/webhooks/sms`
2. **Conversation History**: The system retrieves the last 10 messages from this phone number for context
3. **AI Processing**: The message is processed by the EmergencyAgent (using Google Gemini)
4. **Response**: The agent's response is sent back via SMS (limited to 1600 characters)
5. **Case Creation**: If the agent determines it's an emergency, a case is created in the database
6. **Persistence**: All messages are stored in the database for audit and history

## Conversation Flow Example

```
User: "Hello I need help"
Agent: "Hello. I am here to help you. Please tell me:
1. What is your current location?
2. What is the emergency?
3. Your full name?
4. Your Social Security Number?"

User: "I'm at 123 Main St, my car broke down"
Agent: "I understand you're at 123 Main St with car trouble.
To properly assist you, could you please provide:
- Your full name
- Your Social Security Number
- More details about the car issue"

User: "John Doe, 123-45-6789, engine won't start"
Agent: "✅ Emergency case created! Case ID: abc123...
Category: fuel, Severity: 2/5
📍 Location coordinates: 40.7128, -74.0060
Help is being coordinated. Stay calm and safe."
```

## Troubleshooting

- **No response received**: Check ngrok is running and the webhook URL is correct in Twilio
- **500 errors**: Check the API logs for detailed error messages
- **Agent not responding properly**: Verify Google API keys are set correctly
- **Database errors**: Ensure Supabase connection string is valid

## SMS Limitations

- SMS messages are limited to 1600 characters
- Longer responses will be truncated with "..."
- Rich formatting (bold, links) is not supported in SMS
- Images/media are not processed (MMS not implemented)