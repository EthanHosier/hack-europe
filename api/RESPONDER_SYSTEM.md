# Responder Notification System

## Overview

The emergency response system now includes automatic notification of nearby responders when high-severity emergencies are reported. When someone texts the Twilio number with an emergency, the AI agent not only processes the request but also alerts nearby helpers who can provide immediate assistance.

## How It Works

### 1. Emergency Detection
When someone reports an emergency via SMS, the AI agent:
- Extracts emergency details (type, severity, location)
- Geocodes the location to get coordinates
- Creates an emergency case in the database

### 2. Responder Matching
For high-severity emergencies (level 3+) with location data:
- Searches for active responders within 5km radius
- Filters by relevant specialties based on emergency type:
  - **Medical emergencies** → Doctors, Nurses, EMTs
  - **Fire emergencies** → Firefighters
  - **Crime/violence** → Police
  - **Mental health crises** → Mental Health professionals, Doctors
  - **Rescue situations** → Search & Rescue, Firefighters

### 3. Alert Dispatch
The system automatically:
- Selects up to 3 nearest qualified responders
- Sends SMS alerts with:
  - Distance to emergency
  - Emergency description
  - Exact location and Google Maps link
  - Severity level
  - Case ID for tracking
- Logs notifications in the database

### 4. Response Tracking
Responders can:
- Reply "YES" to confirm they're responding
- View the emergency location on Google Maps
- Coordinate with other responders

## Database Schema

### User Table Extensions
- `latitude`, `longitude`: Current location coordinates
- `last_location_update`: Timestamp of last location update
- `role`: Can be 'Victim', 'Responder', or 'Admin'
- `status`: 'Safe', 'Active', or 'Injured'

### User Specialties
Junction table linking users to their skills:
- Doctor, Nurse, EMT
- Firefighter, Police
- Search & Rescue
- Mental Health
- Mechanic, Electrician
- Translator

## Testing

### Add Test Responders
```bash
cd api
python seed_responders.py
```

This adds 5 test responders in Stockholm with various specialties.

### Test the System
```bash
python test_responder_notification.py
```

Options:
1. **Find nearby responders** - Test the proximity search
2. **Alert system dry run** - Simulate notifications without sending SMS
3. **Send actual test SMS** - Send real test alerts (requires confirmation)

### Test via SMS
1. Text your Twilio number with a high-severity emergency:
   ```
   "I'm at Norrsken House, having a heart attack, need immediate help!"
   ```

2. The system will:
   - Create an emergency case
   - Find nearby medical responders
   - Send them SMS alerts
   - Confirm in the response that responders were notified

## Configuration

### Environment Variables
No additional environment variables needed - uses existing:
- `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_FROM_NUMBER` for SMS
- `GOOGLE_MAPS_API_KEY` for geocoding

### Customization
In `responder_notifier.py`, you can adjust:
- `radius_km`: Search radius (default 5km)
- `max_responders`: Number of responders to notify (default 3)
- Specialty matching logic
- Message templates

## SMS Message Examples

### Emergency Report (from victim)
```
"Help! Car accident at Kungsgatan 10, Stockholm.
Multiple injuries, need ambulance urgently!"
```

### AI Response (to victim)
```
✅ Emergency case created! Case ID: abc123...
Category: medical, Severity: 5/5
📍 Location coordinates: 59.3347, 18.0641

🚨 3 nearby responders have been alerted!
Help is being coordinated. Stay calm and safe.
```

### Alert to Responder
```
🚨 EMERGENCY ALERT

Your help is needed 0.8km away!

Situation: Car accident at Kungsgatan 10, Stockholm. Multiple injuries...
Location: Kungsgatan 10, Stockholm
Maps: https://www.google.com/maps?q=59.3347,18.0641
Type: medical
Severity: 5/5

Case ID: abc123

Reply YES if you can respond.
```

## Privacy & Safety

- Phone numbers are only used for emergency notifications
- Location data is only stored when explicitly provided
- Responders must opt-in by having 'Responder' role and 'Active' status
- All notifications are logged for audit purposes

## Future Enhancements

- Real-time location updates from responders
- Two-way communication between victims and responders
- Responder availability scheduling
- Skills verification system
- Response time tracking
- Multi-language support for international disasters