# EpiPen Allergy Emergency Scenario

## Overview

This scenario simulates an allergic reaction emergency in Northern Sweden where the system needs to find and alert people carrying EpiPens. It demonstrates the system's ability to:

1. Identify allergic reactions from SMS messages
2. Find responders with specific medical supplies (EpiPens)
3. Alert the nearest qualified helpers
4. Provide hospital location for severe cases

## Setup

### Run the Setup Script

```bash
# Using npm
npm run setup:epipen

# Or directly
cd api && python setup_epipen_scenario.py
```

This creates:
- **Gällivare Hospital** resource at coordinates 67.1308, 20.6859
- **4 EPIPEN_HOLDER responders**:
  - Jonathan Eriksson (66.5941, 19.8352) - Near Jokkmokk
  - Julius Andersson (66.4721, 19.6515) - Near Vuollerim
  - Hanyu Wang (67.5923, 18.1055) - Near Stora Sjöfallet
  - Hanxuan Li (67.5980, 18.0255) - Near Ritsem
- **10 regular people** near Stora Sjöfallet National Park (67.5821, 18.1003)

## Geographic Distribution

The scenario covers a large area of Northern Sweden:

```
        Ritsem •  • Stora Sjöfallet
           (Hanxuan)  (Hanyu)
                |
                |  ~50km
                |
         [Emergency Zone]
                |
                |  ~100km
                |
        Jokkmokk •  • Vuollerim
         (Jonathan)  (Julius)
                |
                |  ~60km
                |
         Gällivare Hospital 🏥
```

## Testing the Scenario

### 1. Test Finding EPIPEN Holders

```bash
cd api
python test_epipen_scenario.py
# Choose option 1
```

This searches for EPIPEN holders from various locations.

### 2. Test AI Recognition

```bash
python test_epipen_scenario.py
# Choose option 2
```

Tests if the AI correctly identifies allergic reactions as high-severity medical emergencies.

### 3. Simulate Emergency (Dry Run)

```bash
python test_epipen_scenario.py
# Choose option 3
```

Shows what would happen in a real emergency without sending SMS.

### 4. Send Test SMS

Send an SMS to your Twilio number:

```
"Emergency! Severe allergic reaction at Stora Sjöfallet visitor center,
need EpiPen urgently! Can't breathe, throat swelling!"
```

The system should:
1. Recognize it as a medical emergency (severity 4-5)
2. Find the 2 nearest EPIPEN holders (Hanyu and Hanxuan, ~1km away)
3. Send them SMS alerts with location and maps link
4. Confirm to the victim that help has been alerted

## Expected Behavior

### SMS from Victim
```
"Bee sting, severe allergic reaction, need EpiPen!"
```

### AI Response to Victim
```
I understand you're having a severe allergic reaction from a bee sting.
This is a critical emergency.

To send immediate help, I need:
1. Your exact location
2. Your full name
3. Your social security number

Please provide this information quickly.

[After getting info...]

✅ Emergency case created! Case ID: abc123...
Category: medical, Severity: 5/5
📍 Location coordinates: 67.5821, 18.1003

🚨 2 nearby responders with EpiPens have been alerted!
Help is being coordinated. Stay calm and safe.
```

### Alert to EPIPEN Holder
```
🚨 EMERGENCY ALERT

Your help is needed 1.2km away!

Situation: Severe allergic reaction from bee sting, need EpiPen urgently!
Location: Stora Sjöfallet Visitor Center
Maps: https://www.google.com/maps?q=67.5821,18.1003
Type: medical
Severity: 5/5

BRING YOUR EPIPEN!
Reply YES if you can respond.

Case ID: abc123
```

## How the System Works

### 1. Emergency Detection
The AI agent recognizes keywords:
- "allerg", "anaphyl", "epipen"
- "bee sting", "peanut", "shellfish"
- "throat swelling", "can't breathe"

### 2. Specialty Matching
For allergic reactions, the system prioritizes:
1. **EPIPEN_HOLDER** - People carrying EpiPens
2. **Doctor** - Medical professionals
3. **EMT** - Emergency medical technicians

### 3. Distance Calculation
Uses Haversine formula to find nearest responders within configurable radius (default 50km for sparse Northern Sweden).

### 4. Notification Priority
- Alerts up to 3 responders
- Sorted by distance (nearest first)
- Includes estimated travel time

## Database Schema

### EPIPEN_HOLDER Specialty
```sql
INSERT INTO specialty (name, description)
VALUES ('EPIPEN_HOLDER',
        'Person carrying an EpiPen for emergency allergic reactions');
```

### User Locations
All responders have:
- `latitude` and `longitude` coordinates
- `last_location_update` timestamp
- `status = 'Active'` to receive alerts
- `role = 'Responder'`

## Configuration

In `responder_notifier.py`:
- `radius_km`: Search radius (50km for Northern Sweden)
- `max_responders`: Number to alert (default 3)

## Real-World Application

This scenario demonstrates how the system could:
1. **Save lives** in allergic emergencies where minutes count
2. **Leverage community resources** - people already carrying EpiPens
3. **Work in remote areas** where ambulances are hours away
4. **Coordinate multiple helpers** for better coverage

## Limitations

- Requires responders to have registered and shared location
- SMS delivery depends on cellular coverage
- EpiPen holders must be within reasonable distance
- System can't verify if responders actually have EpiPens with them

## Future Enhancements

- Real-time location tracking for responders
- EpiPen expiry date tracking
- Two-way communication between victim and responders
- Integration with emergency services
- Automated drone delivery of EpiPens