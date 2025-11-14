# CallFlow AI – Outbound Call Center Platform

An intelligent, AI-powered outbound calling platform that automates personalized sales calls using natural language processing and voice technology. The system combines Flask-based web management, Twilio Voice API integration, and OpenAI's GPT for conversation handling.

<img width="1786" height="866" alt="image" src="https://github.com/user-attachments/assets/529ccda1-80b0-4ba7-85f9-e3ada10d72dc" /># Callflow_AI

<img width="1801" height="890" alt="image" src="https://github.com/user-attachments/assets/c67e72fc-4927-4dde-a6b9-7096f9894519" />



## Features

- **AI-Powered Calls**: Uses OpenAI GPT to conduct natural, context-aware conversations with prospects
- **Multi-User Dashboard**: Each company manages their own calling campaigns and meeting schedules
- **Company Customization**: Upload logos, set assistant names, and customize pitch descriptions
- **Meeting Booking**: Prospects can schedule meetings during calls; calendars sync with the platform
- **Call History**: Full logging of all calls and booked meetings for reporting and analysis
- **Flexible Scheduling**: Supports availability windows and timezone-aware meeting slots
- **Voice Integration**: Powered by Twilio for reliable VOIP infrastructure

## Project Structure

```
outbound_call_center_ai/
├── app.py                     # Main Flask web application (accounts, company setup, dashboard)
├── voice_server.py            # Voice handler for Twilio webhooks (call flow, booking)
├── keys.py                    # Environment variable & credential loading (if needed)
│
├── backend/
│   ├── call_service.py        # Twilio API wrapper for initiating outbound calls
│   ├── config.py              # Configuration & environment variable management
│   ├── prompting.py           # System prompt generation & company profile loading
│   ├── scheduler.py           # Meeting scheduling logic & availability slot generation
│   └── __init__.py
│
├── db/
│   ├── db.py                  # SQLite database initialization & schema management
│   ├── assets/                # Static assets directory (logos, backgrounds)
│   │   └── background.jpg     # Company background image (user-defined)
│   ├── data/
│   │   └── meetings_log.json  # JSON log of all booked meetings
│   └── __init__.py
│
├── front/                     # HTML templates (Jinja2)
│   ├── base.html              # Base template (navigation, styling, background injection)
│   ├── index.html             # Landing page
│   ├── login.html             # User login
│   ├── signup.html            # User registration
│   ├── dashboard.html         # Main dashboard (view company, make calls)
│   ├── company_setup.html     # Company profile editor (logo upload, name, description)
│   ├── meetings.html          # View/search booked meetings
│   └── __init__.py
│
├── static/                    # CSS, JS, and other static resources
│
└── README.md                  # This file
```

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Backend** | Python 3.x, Flask |
| **Database** | SQLite |
| **Voice API** | Twilio Voice API |
| **AI/NLP** | OpenAI GPT (gpt-4 or similar) |
| **Frontend** | HTML5, Bootstrap 5, Jinja2 |
| **Authentication** | Session-based (Flask sessions) |

## Getting Started

### User Registration & Setup
1. User signs up with username, email, and password
2. Redirected to company setup page
3. Enter company name, description, and upload logo
4. Save and return to dashboard

### Making a Call
1. User enters prospect phone number (with country code, e.g., +972...)
2. System creates outbound Twilio call to that number
3. Voice server responds with TwiML containing AI prompt
4. GPT conversation module handles real-time responses
5. If prospect agrees, meeting is booked and saved to `meetings_log.json`

### Viewing Meetings:
1. Navigate to "View Booked Meetings"
2. Search by prospect name
3. Delete individual meetings or clear all
4. Data persists in JSON log

